"""Discussion orchestrator entry point — LangGraph-backed.

Workers call run_discussion() or resume_discussion(). Both converge on
_invoke_graph(), which hands control to the LangGraph StateGraph defined in
graph.py. Resumability after worker crashes is handled by the Postgres
checkpointer: re-running with the same thread_id picks up from the last
committed checkpoint automatically.
"""

from __future__ import annotations

import logging

import redis.asyncio as aioredis
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models import Session
from app.llm.router import LLMRouter
from app.orchestrator.graph import DiscussionState, build_discussion_graph
from app.orchestrator.state_machine import StateMachine
from app.panels.schemas import PanelSchema

logger = logging.getLogger(__name__)
settings = get_settings()


def _pg_conn_string() -> str:
    """Return a psycopg3-compatible connection string for the checkpointer.

    SQLAlchemy URLs use 'postgresql+asyncpg://...' but AsyncPostgresSaver
    expects a bare 'postgresql://...' or 'postgres://...' string.
    """
    url = settings.database_url
    for prefix in ("postgresql+asyncpg://", "postgres+asyncpg://"):
        if url.startswith(prefix):
            return "postgresql://" + url[len(prefix):]
    return url


class DiscussionOrchestrator:
    """Thin wrapper: creates the LangGraph graph and runs it for a session."""

    def __init__(
        self,
        db: AsyncSession,
        redis_client: aioredis.Redis,
        router: LLMRouter,
    ) -> None:
        self._db = db
        self._redis = redis_client
        self._router = router

    async def run_discussion(self, session_id: str) -> None:
        """Start a new discussion from scratch."""
        session = await self._load_session(session_id)
        if not session:
            logger.warning("run_discussion: session %s not found", session_id)
            return

        panel = PanelSchema.model_validate(session.panel_snapshot_json)

        initial_state: DiscussionState = {
            "session_id": session_id,
            "topic": session.topic,
            "panel_snapshot": session.panel_snapshot_json,
            "current_phase": "opening",
            "turn_count": 0,
            "last_speaker": None,
            "next_speaker": None,
            "next_inject_challenge": False,
            "challenges_this_phase": 0,
            "summary_counter": 0,
            "commitments": {},
            "pending_interventions": [],
            "should_conclude": False,
            "should_vote": False,
            "cost_cap_hit": False,
        }

        await self._invoke_graph(session_id, initial_state)

    async def resume_discussion(self, session_id: str) -> None:
        """Resume a paused or crash-interrupted discussion.

        Because the Postgres checkpointer persists state after every node,
        passing the same thread_id restores execution exactly where it stopped.
        The initial_state here is only used if there is no existing checkpoint
        (i.e. the graph has never run for this thread_id), which should not
        happen for a genuine resume — but serves as a safe fallback.
        """
        session = await self._load_session(session_id)
        if not session or session.status not in ("paused", "queued", "running"):
            logger.warning(
                "resume_discussion: session %s not found or in non-resumable status", session_id
            )
            return

        if session.status != "running":
            await StateMachine.transition_status(self._db, session, "running")
            await self._db.commit()

        # The graph will restore its own state from the checkpointer.
        # We pass an empty-ish initial state; it is ignored when a checkpoint exists.
        fallback_state: DiscussionState = {
            "session_id": session_id,
            "topic": session.topic,
            "panel_snapshot": session.panel_snapshot_json,
            "current_phase": session.phase or "opening",
            "turn_count": 0,
            "last_speaker": None,
            "next_speaker": None,
            "next_inject_challenge": False,
            "challenges_this_phase": 0,
            "summary_counter": 0,
            "commitments": {},
            "pending_interventions": [],
            "should_conclude": False,
            "should_vote": False,
            "cost_cap_hit": False,
        }

        await self._invoke_graph(session_id, fallback_state)

    async def inject_intervention(
        self,
        session_id: str,
        intervention: dict,
    ) -> None:
        """No-op acknowledgment: the intervention is already in the messages table.

        The check_interventions node queries the DB at the start of every agent
        turn and will pick up the new message automatically. This method exists
        as a hook for future logic (e.g., wake-up signaling if the worker is
        idle) without requiring a call-site change.
        """
        logger.debug(
            "inject_intervention: session %s intervention will be picked up at next turn",
            session_id,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _invoke_graph(
        self,
        session_id: str,
        initial_state: DiscussionState,
    ) -> None:
        """Build the checkpointer, compile the graph, and run it to completion."""
        async with AsyncPostgresSaver.from_conn_string(_pg_conn_string()) as checkpointer:
            graph = build_discussion_graph(
                db=self._db,
                redis_client=self._redis,
                router=self._router,
                checkpointer=checkpointer,
            )
            config = {"configurable": {"thread_id": session_id}, "recursion_limit": 150}
            try:
                await graph.ainvoke(initial_state, config=config)
            except Exception:
                logger.exception(
                    "Graph execution failed for session %s; state checkpointed at last node",
                    session_id,
                )
                raise

    async def _load_session(self, session_id: str) -> Session | None:
        result = await self._db.execute(
            select(Session)
            .where(Session.id == session_id)
            .execution_options(populate_existing=True)
        )
        return result.scalar_one_or_none()
