"""LangGraph discussion graph.

Defines the StateGraph that replaces the hand-rolled discussion loop.
Each node calls the same underlying agents/runners the rest of the system uses.
The Postgres checkpointer gives resumability after worker crashes for free.
Human interventions are written to the DB by the API layer; the
check_interventions node queries the DB at the start of every agent turn
and carries new messages into the turn's context automatically.
"""

from __future__ import annotations

import json
import uuid
from typing import Annotated, Any, TypedDict

import redis.asyncio as aioredis
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import END, StateGraph
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models import AuditEvent, Message, Outcome, Session, Vote
from app.llm.router import LLMRouter
from app.orchestrator.agent_runner import AgentRunner
from app.orchestrator.moderator import ModeratorAgent
from app.orchestrator.schemas import TurnContext
from app.orchestrator.state_machine import StateMachine
from app.panels.schemas import PanelSchema, SeatConfig
from app.tools.registry import ToolRegistry


# ---------------------------------------------------------------------------
# State schema
# ---------------------------------------------------------------------------

def _merge_interventions(left: list[dict], right: list[dict]) -> list[dict]:
    """Reducer: extend pending interventions rather than replacing them."""
    return left + right


class DiscussionState(TypedDict):
    session_id: str
    topic: str
    panel_snapshot: dict[str, Any]
    current_phase: str
    turn_count: int
    last_speaker: str | None
    # Written by moderator_turn, consumed by agent_turn
    next_speaker: str | None
    next_inject_challenge: bool
    challenges_this_phase: int
    summary_counter: int
    commitments: dict[str, str]
    # Interventions accumulate via the reducer so concurrent writes don't race
    pending_interventions: Annotated[list[dict[str, Any]], _merge_interventions]
    # Signals from nodes to the routing function
    should_conclude: bool
    should_vote: bool
    cost_cap_hit: bool


# ---------------------------------------------------------------------------
# Node helpers (thin wrappers that need DB + Redis; injected at build time)
# ---------------------------------------------------------------------------

class _NodeContext:
    """Holds collaborators so node closures can access them without globals."""

    def __init__(
        self,
        db: AsyncSession,
        redis_client: aioredis.Redis,
        router: LLMRouter,
    ) -> None:
        self.db = db
        self.redis = redis_client
        self.router = router


async def _publish(redis_client: aioredis.Redis, session_id: str, event: dict[str, Any]) -> None:
    await redis_client.publish(f"discussion:{session_id}", json.dumps(event))


async def _load_session(db: AsyncSession, session_id: str) -> Session | None:
    result = await db.execute(
        select(Session)
        .where(Session.id == session_id)
        .execution_options(populate_existing=True)
    )
    return result.scalar_one_or_none()


async def _save_message(
    db: AsyncSession,
    *,
    session_id: str,
    seat_id: str | None,
    author_type: str,
    content: str,
    model: str | None = None,
    tokens_in: int = 0,
    tokens_out: int = 0,
    cost_usd: float = 0.0,
    latency_ms: int = 0,
    phase: str | None = None,
    reasoning: dict[str, Any] | None = None,
    sources_cited: list[Any] | None = None,
) -> str:
    msg_id = str(uuid.uuid4())
    msg = Message(
        id=msg_id,
        session_id=session_id,
        seat_id=seat_id,
        author_type=author_type,
        content=content,
        reasoning_json=reasoning or {},
        sources_cited_json=sources_cited or [],
        model=model,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost_usd=cost_usd,
        latency_ms=latency_ms,
        phase_at_creation=phase,
    )
    db.add(msg)
    await db.flush()
    return msg_id


async def _get_history(db: AsyncSession, session_id: str, limit: int = 50) -> list[dict[str, Any]]:
    result = await db.execute(
        select(Message)
        .where(
            Message.session_id == session_id,
            Message.author_type.in_(["agent", "human", "moderator", "system"]),
        )
        .order_by(Message.created_at.desc())
        .limit(limit * 2)
    )
    all_messages = list(reversed(result.scalars().all()))
    visible = [
        m for m in all_messages
        if not (isinstance(m.reasoning_json, dict) and m.reasoning_json.get("hidden_commitment"))
    ]
    return [
        {
            "id": m.id,
            "seat_id": m.seat_id,
            "author_type": m.author_type,
            "content": m.content,
            "phase": m.phase_at_creation,
        }
        for m in visible[-limit:]
    ]


async def _build_history_summary(db: AsyncSession, session_id: str, limit: int = 20) -> str:
    result = await db.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    messages = list(reversed(result.scalars().all()))
    lines = [
        f"[{m.seat_id or 'unknown'}]: {(m.content or '')[:200]}"
        for m in messages
    ]
    return "\n".join(lines)


async def _get_pending_interventions(db: AsyncSession, session_id: str) -> list[dict[str, Any]]:
    ts_result = await db.execute(
        select(Message.created_at)
        .where(
            Message.session_id == session_id,
            Message.author_type == "agent",
        )
        .order_by(Message.created_at.desc())
        .limit(1)
    )
    last_agent_ts = ts_result.scalar_one_or_none()

    query = select(Message).where(
        Message.session_id == session_id,
        Message.author_type == "human",
    )
    if last_agent_ts is not None:
        query = query.where(Message.created_at > last_agent_ts)
    query = query.order_by(Message.created_at).limit(10)

    result = await db.execute(query)
    interventions = []
    for msg in result.scalars().all():
        reasoning = msg.reasoning_json if isinstance(msg.reasoning_json, dict) else {}
        interventions.append({
            "message_id": msg.id,
            "user_name": reasoning.get("user_name", "Human"),
            "content": msg.content,
            "target_seat": reasoning.get("target_seat"),
        })
    return interventions


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------

def build_discussion_graph(
    db: AsyncSession,
    redis_client: aioredis.Redis,
    router: LLMRouter,
    checkpointer: AsyncPostgresSaver,
) -> Any:
    """Construct and compile the discussion StateGraph.

    Returns a compiled LangGraph graph. Each call to graph.ainvoke() or
    graph.astream() with a thread_id config resumes from the last checkpoint.
    """
    nc = _NodeContext(db=db, redis_client=redis_client, router=router)

    # ------------------------------------------------------------------
    # Node: commit_phase
    # ------------------------------------------------------------------
    async def commit_phase(state: DiscussionState) -> dict[str, Any]:
        """Run the hidden-commitment protocol before opening statements."""
        panel = PanelSchema.model_validate(state["panel_snapshot"])
        if not panel.discussion_rules.hidden_position_protocol:
            return {"commitments": {}}

        session_id = state["session_id"]
        topic = state["topic"]
        commit_prompt = (
            f"Topic for discussion: {topic}\n\n"
            "Based only on this topic and your persona, state your initial position "
            "in one concise sentence. Do not elaborate yet."
        )

        commitments: dict[str, str] = {}
        for seat in panel.seats:
            client = nc.router.get_client(seat.model)
            response = await client.chat(
                model=seat.model,
                messages=[{"role": "user", "content": commit_prompt}],
                system=seat.persona.system_prompt_overlay,
                max_tokens=2048,
            )
            commitment = response.get("content", "")
            commitments[seat.seat_id] = commitment

            msg_id = await _save_message(
                nc.db,
                session_id=session_id,
                seat_id=seat.seat_id,
                author_type="agent",
                content=commitment,
                model=seat.model,
                tokens_in=response.get("input_tokens", 0),
                tokens_out=response.get("output_tokens", 0),
                cost_usd=response.get("cost_usd", 0.0),
                latency_ms=response.get("latency_ms", 0),
                phase="opening",
                reasoning={"hidden_commitment": True},
            )

            await _publish(nc.redis, session_id, {
                "event": "message",
                "data": {
                    "message_id": msg_id,
                    "session_id": session_id,
                    "seat_id": seat.seat_id,
                    "author_type": "agent",
                    "content": commitment,
                    "phase": "opening",
                }
            })
        await nc.db.commit()
        return {"commitments": commitments}

    # ------------------------------------------------------------------
    # Node: opening_phase
    # ------------------------------------------------------------------
    async def opening_phase(state: DiscussionState) -> dict[str, Any]:
        """Transition the session to running + opening phase, publish event."""
        session_id = state["session_id"]
        session = await _load_session(nc.db, session_id)
        if not session:
            return {}

        if session.status != "running":
            await StateMachine.transition_status(nc.db, session, "running")
        await StateMachine.transition_phase(nc.db, session, "opening")
        await nc.db.commit()

        await _publish(nc.redis, session_id, {
            "event": "session_state",
            "data": {"status": "running", "phase": "opening"},
        })
        await _publish(nc.redis, session_id, {
            "event": "phase_change",
            "data": {"from": None, "to": "opening", "summary": None},
        })
        return {"current_phase": "opening"}

    # ------------------------------------------------------------------
    # Node: check_interventions
    # Query the DB for human messages written since the last agent turn.
    # Human interventions are written to DB by the API (via WebSocket/REST);
    # the graph picks them up here at the start of each turn. No interrupt()
    # needed: the discussion loop is naturally gated by LLM call latency, so
    # interventions written between turns are reliably collected here.
    # ------------------------------------------------------------------
    async def check_interventions(state: DiscussionState) -> dict[str, Any]:
        session_id = state["session_id"]
        db_interventions = await _get_pending_interventions(nc.db, session_id)
        for iv in db_interventions:
            await _publish(nc.redis, session_id, {"event": "intervention", "data": iv})
        return {"pending_interventions": db_interventions}

    # ------------------------------------------------------------------
    # Node: moderator_turn
    # ------------------------------------------------------------------
    async def moderator_turn(state: DiscussionState) -> dict[str, Any]:
        panel = PanelSchema.model_validate(state["panel_snapshot"])
        rules = panel.discussion_rules
        mod_cfg = panel.moderator_config
        session_id = state["session_id"]

        # Check if session was force-ended externally
        session = await _load_session(nc.db, session_id)
        if not session:
            return {"should_conclude": True}
        if session.status in ("voting", "concluded", "failed"):
            return {"should_conclude": True}

        # Cost cap check
        if session.cost_limit and (session.cost_actual or 0) >= session.cost_limit:
            await StateMachine.transition_status(nc.db, session, "paused")
            await nc.db.commit()
            await _publish(nc.redis, session_id, {
                "event": "cost_cap_hit",
                "data": {
                    "cost_actual": session.cost_actual,
                    "cost_limit": session.cost_limit,
                },
            })
            return {"cost_cap_hit": True, "should_conclude": True}

        # Max-turns guard
        if state["turn_count"] >= rules.max_turns:
            return {"should_vote": True}

        # Auto-summary
        auto_summary_every = mod_cfg.auto_summary_every_n_turns
        summary_counter = state["summary_counter"]
        if auto_summary_every > 0 and summary_counter >= auto_summary_every:
            recent_result = await nc.db.execute(
                select(Message)
                .where(Message.session_id == session_id)
                .order_by(Message.created_at.desc())
                .limit(auto_summary_every)
            )
            recent = [{"seat_id": m.seat_id, "content": m.content}
                      for m in reversed(recent_result.scalars().all())]
            moderator = ModeratorAgent(
                router=nc.router,
                model=mod_cfg.model,
                system_prompt=mod_cfg.system_prompt,
            )
            summary_text = await moderator.generate_summary(state["topic"], recent)
            if summary_text:
                await _save_message(
                    nc.db,
                    session_id=session_id,
                    seat_id=None,
                    author_type="system",
                    content=f"[Auto-Summary] {summary_text}",
                    phase=state["current_phase"],
                )
                await _publish(nc.redis, session_id, {
                    "event": "summary_ready",
                    "data": {"summary": summary_text, "turn_range_end": state["turn_count"]},
                })
            summary_counter = 0

        # Moderator decision
        seat_ids = [s.seat_id for s in panel.seats]
        devil_advocate = panel.get_devil_advocate()
        devil_advocate_seat = devil_advocate.seat_id if devil_advocate else None
        history_summary = await _build_history_summary(nc.db, session_id)

        moderator = ModeratorAgent(
            router=nc.router,
            model=mod_cfg.model,
            system_prompt=mod_cfg.system_prompt,
        )
        decision = await moderator.decide_next_turn(
            topic=state["topic"],
            current_phase=state["current_phase"],
            turn_count=state["turn_count"],
            seat_ids=seat_ids,
            history_summary=history_summary,
            last_speaker=state["last_speaker"],
            challenges_this_phase=state["challenges_this_phase"],
            convergence_speed_threshold=rules.min_turns_before_convergence,
            min_turns_before_convergence=rules.min_turns_before_convergence,
            has_devil_advocate=panel.has_devil_advocate(),
            devil_advocate_seat=devil_advocate_seat,
        )

        updates: dict[str, Any] = {
            "summary_counter": summary_counter,
            "next_speaker": decision.next_speaker,
            "next_inject_challenge": decision.inject_challenge,
        }

        # Phase transition
        if decision.phase_transition and decision.phase_transition != state["current_phase"]:
            session = await _load_session(nc.db, session_id)
            if session:
                await StateMachine.transition_phase(
                    nc.db, session, decision.phase_transition, decision.summary
                )
                await nc.db.commit()
            await _publish(nc.redis, session_id, {
                "event": "phase_change",
                "data": {
                    "from": state["current_phase"],
                    "to": decision.phase_transition,
                    "summary": decision.summary,
                },
            })
            updates["current_phase"] = decision.phase_transition
            updates["challenges_this_phase"] = 0

            if decision.phase_transition == "vote":
                updates["should_vote"] = True
                return updates

        if decision.inject_challenge:
            updates["challenges_this_phase"] = state["challenges_this_phase"] + 1

        return updates

    # ------------------------------------------------------------------
    # Node: agent_turn
    # ------------------------------------------------------------------
    async def agent_turn(state: DiscussionState) -> dict[str, Any]:
        panel = PanelSchema.model_validate(state["panel_snapshot"])
        rules = panel.discussion_rules
        mod_cfg = panel.moderator_config
        session_id = state["session_id"]

        next_speaker = state["next_speaker"]
        if not next_speaker:
            return {"turn_count": state["turn_count"] + 1, "pending_interventions": []}

        seat_map: dict[str, SeatConfig] = {s.seat_id: s for s in panel.seats}
        seat = seat_map.get(next_speaker)
        if not seat:
            return {"turn_count": state["turn_count"] + 1, "pending_interventions": []}

        tool_registry = await ToolRegistry.build_for_session(
            panel_config={"allowed_tools": rules.allowed_tools},
            settings=get_settings(),
        )
        runner = AgentRunner(
            router=nc.router,
            tool_registry=tool_registry,
            redis_client=nc.redis,
            adversarial_framing=rules.adversarial_framing,
        )

        await _publish(nc.redis, session_id, {
            "event": "speaker_change",
            "data": {"seat_id": seat.seat_id},
        })

        history = await _get_history(nc.db, session_id)
        ctx = TurnContext(
            session_id=session_id,
            seat_id=seat.seat_id,
            phase=state["current_phase"],
            topic=state["topic"],
            hidden_commitment=state["commitments"].get(seat.seat_id),
            history=history,
            pending_interventions=state["pending_interventions"],
            inject_challenge=state["next_inject_challenge"],
            persona_system_prompt=seat.persona.system_prompt_overlay,
            allowed_tools=rules.allowed_tools,
        )

        llm_response = await runner.run_turn(ctx=ctx, model=seat.model)

        await _save_message(
            nc.db,
            session_id=session_id,
            seat_id=seat.seat_id,
            author_type="agent",
            content=llm_response["content"],
            model=llm_response["model"],
            tokens_in=llm_response["input_tokens"],
            tokens_out=llm_response["output_tokens"],
            cost_usd=llm_response["cost_usd"],
            latency_ms=llm_response["latency_ms"],
            phase=state["current_phase"],
        )

        # Update session cost
        session = await _load_session(nc.db, session_id)
        if session:
            session.cost_actual = (session.cost_actual or 0.0) + llm_response["cost_usd"]
        await nc.db.commit()

        await _publish(nc.redis, session_id, {
            "event": "cost_update",
            "data": {
                "cost_actual": session.cost_actual if session else 0,
                "cost_estimate": session.cost_estimate if session else None,
                "cost_limit": session.cost_limit if session else None,
            },
        })

        return {
            "last_speaker": next_speaker,
            "turn_count": state["turn_count"] + 1,
            "summary_counter": state["summary_counter"] + 1,
            "pending_interventions": [],   # consumed
        }

    # ------------------------------------------------------------------
    # Node: voting_phase
    # ------------------------------------------------------------------
    async def voting_phase(state: DiscussionState) -> dict[str, Any]:
        panel = PanelSchema.model_validate(state["panel_snapshot"])
        mod_cfg = panel.moderator_config
        session_id = state["session_id"]

        session = await _load_session(nc.db, session_id)
        if not session:
            return {"should_conclude": True}

        # If already in voting/concluded (force-ended externally), skip
        if session.status in ("voting", "concluded"):
            return {"should_conclude": True}

        await StateMachine.transition_status(nc.db, session, "voting")
        await nc.db.commit()

        history_summary = await _build_history_summary(nc.db, session_id)
        moderator = ModeratorAgent(
            router=nc.router,
            model=mod_cfg.model,
            system_prompt=mod_cfg.system_prompt,
        )
        recommendation = await moderator.generate_recommendation(
            topic=state["topic"],
            history_summary=history_summary,
            vote_tally={},
        )

        await _save_message(
            nc.db,
            session_id=session_id,
            seat_id=None,
            author_type="system",
            content=f"[Proposed Recommendation] {recommendation.statement}",
            phase="vote",
        )

        agent_votes: dict[str, dict[str, str]] = {}
        yes_count = no_count = abstain_count = 0

        for seat in panel.seats:
            vote_decision = await moderator.get_agent_vote(
                seat_id=seat.seat_id,
                model=seat.model,
                system_prompt=seat.persona.system_prompt_overlay,
                topic=state["topic"],
                recommendation=recommendation,
                history_summary=history_summary,
            )
            agent_votes[seat.seat_id] = {
                "vote": vote_decision.vote,
                "rationale": vote_decision.rationale,
            }
            if vote_decision.vote == "yes":
                yes_count += 1
            elif vote_decision.vote == "no":
                no_count += 1
            else:
                abstain_count += 1

            vote_row = Vote(
                id=str(uuid.uuid4()),
                session_id=session_id,
                voter_id=seat.seat_id,
                voter_type="agent",
                recommendation_version=1,
                vote=vote_decision.vote,
                rationale=vote_decision.rationale,
            )
            nc.db.add(vote_row)
            await nc.db.flush()

            await _publish(nc.redis, session_id, {
                "event": "vote_update",
                "data": {
                    "voter_type": "agent",
                    "voter_id": seat.seat_id,
                    "vote": vote_decision.vote,
                    "running_tally": {"yes": yes_count, "no": no_count, "abstain": abstain_count},
                },
            })

        total = yes_count + no_count + abstain_count
        confidence_score = (yes_count / total) if total else 0.0

        source_result = await nc.db.execute(
            select(Message).where(
                Message.session_id == session_id,
                Message.author_type == "agent",
            )
        )
        agent_msgs = source_result.scalars().all()
        with_sources = sum(
            1 for m in agent_msgs
            if isinstance(m.sources_cited_json, list) and len(m.sources_cited_json) > 0
        )
        source_density = (with_sources / len(agent_msgs)) if agent_msgs else 0.0

        outcome = Outcome(
            id=str(uuid.uuid4()),
            session_id=session_id,
            type=recommendation.outcome_type,
            statement=recommendation.statement,
            supporting_arguments_json=recommendation.supporting_arguments,
            substantive_dissents_json=recommendation.substantive_dissents,
            agent_vote_summary_json={
                "yes": yes_count,
                "no": no_count,
                "abstain": abstain_count,
                "votes": agent_votes,
            },
            human_vote_summary_json={},
            divergence_noted=False,
            confidence_score=confidence_score,
            source_density_score=source_density,
        )
        nc.db.add(outcome)

        session = await _load_session(nc.db, session_id)
        if session:
            await StateMachine.transition_status(nc.db, session, "concluded")
        audit = AuditEvent(
            id=str(uuid.uuid4()),
            session_id=session_id,
            actor_type="system",
            event_type="session_concluded",
            payload_json={
                "outcome_type": recommendation.outcome_type,
                "confidence_score": confidence_score,
            },
        )
        nc.db.add(audit)
        await nc.db.commit()

        await _publish(nc.redis, session_id, {
            "event": "session_state",
            "data": {
                "status": "concluded",
                "outcome": {
                    "type": recommendation.outcome_type,
                    "statement": recommendation.statement,
                    "confidence_score": confidence_score,
                },
            },
        })
        return {"should_conclude": True}

    # ------------------------------------------------------------------
    # Routing functions
    # ------------------------------------------------------------------
    def route_after_moderator(state: DiscussionState) -> str:
        if state.get("should_conclude") or state.get("cost_cap_hit"):
            return END
        if state.get("should_vote"):
            return "voting_phase"
        return "check_interventions"

    def route_after_agent(state: DiscussionState) -> str:
        if state.get("should_conclude"):
            return END
        return "moderator_turn"

    # ------------------------------------------------------------------
    # Graph assembly
    # ------------------------------------------------------------------
    sg = StateGraph(DiscussionState)

    sg.add_node("commit_phase", commit_phase)
    sg.add_node("opening_phase", opening_phase)
    sg.add_node("check_interventions", check_interventions)
    sg.add_node("moderator_turn", moderator_turn)
    sg.add_node("agent_turn", agent_turn)
    sg.add_node("voting_phase", voting_phase)

    sg.set_entry_point("commit_phase")
    sg.add_edge("commit_phase", "opening_phase")
    sg.add_edge("opening_phase", "moderator_turn")
    sg.add_conditional_edges("moderator_turn", route_after_moderator, {
        "check_interventions": "check_interventions",
        "voting_phase": "voting_phase",
        END: END,
    })
    sg.add_edge("check_interventions", "agent_turn")
    sg.add_conditional_edges("agent_turn", route_after_agent, {
        "moderator_turn": "moderator_turn",
        END: END,
    })
    sg.add_edge("voting_phase", END)

    return sg.compile(checkpointer=checkpointer)
