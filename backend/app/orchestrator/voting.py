"""Standalone voting phase — used when a session is force-ended by the user."""

from __future__ import annotations

import json
import logging
import uuid

import redis.asyncio as aioredis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuditEvent, Message, Outcome, Session, Vote
from app.llm.router import LLMRouter
from app.orchestrator.moderator import ModeratorAgent
from app.orchestrator.state_machine import StateMachine
from app.panels.schemas import PanelSchema

logger = logging.getLogger(__name__)


async def _publish(redis_client: aioredis.Redis, session_id: str, event: dict) -> None:
    await redis_client.publish(f"discussion:{session_id}", json.dumps(event))


async def run_voting_phase(
    db: AsyncSession,
    redis_client: aioredis.Redis,
    router: LLMRouter,
    session_id: str,
) -> None:
    """Generate recommendation, collect agent votes, create outcome, conclude."""
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        logger.warning("run_voting_phase: session %s not found", session_id)
        return

    panel = PanelSchema.model_validate(session.panel_snapshot_json)
    mod_cfg = panel.moderator_config

    # Build history summary from recent messages
    msg_result = await db.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at.desc())
        .limit(50)
    )
    recent_msgs = msg_result.scalars().all()
    history_lines = []
    for m in reversed(recent_msgs):
        label = m.seat_id or m.author_type
        history_lines.append(f"[{label}]: {m.content[:500]}")
    history_summary = "\n".join(history_lines)

    # Generate recommendation
    moderator = ModeratorAgent(
        router=router,
        model=mod_cfg.model,
        system_prompt=mod_cfg.system_prompt,
    )
    recommendation = await moderator.generate_recommendation(
        topic=session.topic,
        history_summary=history_summary,
        vote_tally={},
    )

    await db.execute(
        Message.__table__.insert().values(
            id=str(uuid.uuid4()),
            session_id=session_id,
            seat_id=None,
            author_type="system",
            content=f"[Proposed Recommendation] {recommendation.statement}",
            phase_at_creation="vote",
        )
    )
    await db.flush()

    # Collect agent votes
    agent_votes: dict[str, dict[str, str]] = {}
    yes_count = no_count = abstain_count = 0

    for seat in panel.seats:
        vote_decision = await moderator.get_agent_vote(
            seat_id=seat.seat_id,
            model=seat.model,
            system_prompt=seat.persona.system_prompt_overlay,
            topic=session.topic,
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
        db.add(vote_row)
        await db.flush()

        await _publish(redis_client, session_id, {
            "event": "vote_update",
            "data": {
                "voter_type": "agent",
                "voter_id": seat.seat_id,
                "voter_name": seat.display_name,
                "seat_id": seat.seat_id,
                "vote": vote_decision.vote,
                "rationale": vote_decision.rationale,
                "running_tally": {"yes": yes_count, "no": no_count, "abstain": abstain_count},
            },
        })

    # Compute scores
    total = yes_count + no_count + abstain_count
    confidence_score = (yes_count / total) if total else 0.0

    agent_msg_result = await db.execute(
        select(Message).where(
            Message.session_id == session_id,
            Message.author_type == "agent",
        )
    )
    agent_msgs = agent_msg_result.scalars().all()
    with_sources = sum(
        1 for m in agent_msgs
        if isinstance(m.sources_cited_json, list) and len(m.sources_cited_json) > 0
    )
    source_density = (with_sources / len(agent_msgs)) if agent_msgs else 0.0

    # Create outcome
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
    db.add(outcome)

    # Transition to concluded
    # Re-fetch session to get current status
    result = await db.execute(
        select(Session)
        .where(Session.id == session_id)
        .execution_options(populate_existing=True)
    )
    session = result.scalar_one_or_none()
    if session:
        await StateMachine.transition_status(db, session, "concluded")

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
    db.add(audit)
    await db.commit()

    await _publish(redis_client, session_id, {
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
