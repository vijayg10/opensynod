"""Arq worker functions for discussion orchestration (LangGraph-backed)."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


async def run_discussion(ctx: dict[str, Any], session_id: str) -> None:
    """Start and run a new discussion session."""
    from app.llm.router import LLMRouter
    from app.orchestrator.discussion import DiscussionOrchestrator

    redis_client = ctx["pubsub_redis"]

    try:
        async with ctx["session_factory"]() as db:
            orchestrator = DiscussionOrchestrator(
                db=db,
                redis_client=redis_client,
                router=LLMRouter(),
            )
            await orchestrator.run_discussion(session_id)
    except Exception as exc:
        logger.exception("run_discussion failed for session %s: %s", session_id, exc)
        await _mark_failed(ctx, session_id, error_message=str(exc))
        raise


async def resume_discussion(ctx: dict[str, Any], session_id: str) -> None:
    """Resume a paused or crash-interrupted discussion.

    Because the LangGraph Postgres checkpointer persisted state at the last
    completed node, this call re-enters the graph at exactly that point — no
    manual state reconstruction needed.
    """
    from app.llm.router import LLMRouter
    from app.orchestrator.discussion import DiscussionOrchestrator

    redis_client = ctx["pubsub_redis"]

    try:
        async with ctx["session_factory"]() as db:
            orchestrator = DiscussionOrchestrator(
                db=db,
                redis_client=redis_client,
                router=LLMRouter(),
            )
            await orchestrator.resume_discussion(session_id)
    except Exception as exc:
        logger.exception("resume_discussion failed for session %s: %s", session_id, exc)
        await _mark_failed(ctx, session_id, error_message=str(exc))
        raise


async def run_voting(ctx: dict[str, Any], session_id: str) -> None:
    """Run the voting phase for a force-ended session."""
    from app.llm.router import LLMRouter
    from app.orchestrator.voting import run_voting_phase

    redis_client = ctx["pubsub_redis"]

    try:
        async with ctx["session_factory"]() as db:
            await run_voting_phase(
                db=db,
                redis_client=redis_client,
                router=LLMRouter(),
                session_id=session_id,
            )
    except Exception as exc:
        logger.exception("run_voting failed for session %s: %s", session_id, exc)
        await _mark_failed(ctx, session_id, error_message=str(exc))
        raise


async def inject_intervention(
    ctx: dict[str, Any],
    session_id: str,
    intervention: dict[str, Any],
) -> None:
    """Push a human intervention into a graph suspended at check_interventions."""
    from app.llm.router import LLMRouter
    from app.orchestrator.discussion import DiscussionOrchestrator

    redis_client = ctx["pubsub_redis"]

    try:
        async with ctx["session_factory"]() as db:
            orchestrator = DiscussionOrchestrator(
                db=db,
                redis_client=redis_client,
                router=LLMRouter(),
            )
            await orchestrator.inject_intervention(session_id, intervention)
    except Exception as exc:
        logger.exception("inject_intervention failed for session %s: %s", session_id, exc)
        raise


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

async def _mark_failed(ctx: dict[str, Any], session_id: str, error_message: str | None = None) -> None:
    try:
        import json

        from sqlalchemy import select

        from app.db.models import Session
        from app.orchestrator.state_machine import StateMachine

        async with ctx["session_factory"]() as fail_db:
            result = await fail_db.execute(select(Session).where(Session.id == session_id))
            db_session = result.scalar_one_or_none()
            if db_session and db_session.status in ("running", "queued"):
                await StateMachine.transition_status(
                    fail_db,
                    db_session,
                    "failed",
                    payload={"error": error_message} if error_message else None,
                )
                await fail_db.commit()

                # Notify frontend via SSE
                redis_client = ctx["pubsub_redis"]
                await redis_client.publish(
                    f"discussion:{session_id}",
                    json.dumps({
                        "event": "session_state",
                        "data": {
                            "status": "failed",
                            "error": error_message,
                        }
                    }),
                )
    except Exception:
        logger.exception("Failed to mark session %s as failed", session_id)
