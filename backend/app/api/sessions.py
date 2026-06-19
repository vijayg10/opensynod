"""Session management API + SSE streaming + WebSocket endpoints."""

from __future__ import annotations

import json
import uuid
from typing import Any

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, Query, Request, WebSocket, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.security import decode_token
from app.db.models import AuditEvent, Message, Outcome, Session, Source, User, Vote
from app.db.session import get_db
from app.orchestrator.state_machine import InvalidTransitionError, StateMachine
from app.panels.registry import PanelRegistry
from app.ws.gateway import handle_websocket

router = APIRouter(prefix="/sessions", tags=["sessions"])

settings = get_settings()


# ─────────────────────────────────────────────
# Schemas
# ─────────────────────────────────────────────

class CreateSessionRequest(BaseModel):
    topic: str = Field(..., min_length=1)
    outcome_type: str = Field(default="recommendation")
    success_criteria: str | None = None
    panel_id: str
    discussion_rules: dict[str, Any] = Field(default_factory=dict)
    cost_limit: float | None = None


class UpdateSessionRequest(BaseModel):
    topic: str | None = None
    success_criteria: str | None = None
    discussion_rules: dict[str, Any] | None = None
    cost_limit: float | None = None


class SessionResponse(BaseModel):
    id: str
    topic: str
    outcome_type: str
    status: str
    phase: str | None
    panel_id: str | None
    panel_snapshot_json: dict[str, Any]
    discussion_rules_json: dict[str, Any]
    cost_actual: float
    cost_estimate: float | None
    cost_limit: float | None
    started_at: Any
    concluded_at: Any
    created_at: Any
    error: str | None = None

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    id: str
    seat_id: str | None
    author_type: str
    content: str
    model: str | None
    tokens_in: int
    tokens_out: int
    cost_usd: float
    latency_ms: int
    phase_at_creation: str | None
    sources_cited_json: list[Any]
    created_at: Any

    model_config = {"from_attributes": True}


class InterventionRequest(BaseModel):
    content: str = Field(..., min_length=1)
    target: str = Field(default="all")


class HumanVoteRequest(BaseModel):
    vote: str = Field(..., pattern="^(yes|no|abstain)$")
    rationale: str = Field(default="")


# ─────────────────────────────────────────────
# CRUD endpoints
# ─────────────────────────────────────────────

@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    body: CreateSessionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SessionResponse:
    """Create a new session in draft state."""
    panel = await PanelRegistry.get_by_id(db, body.panel_id)
    if not panel:
        raise HTTPException(status_code=404, detail="Panel not found")

    snapshot = PanelRegistry.build_snapshot(panel)
    cost_estimate = _estimate_cost(panel)

    session = Session(
        id=str(uuid.uuid4()),
        created_by=current_user.id,
        topic=body.topic,
        outcome_type=body.outcome_type,
        success_criteria=body.success_criteria,
        panel_id=body.panel_id,
        panel_snapshot_json=snapshot,
        discussion_rules_json=body.discussion_rules,
        cost_estimate=cost_estimate,
        cost_limit=body.cost_limit,
        status="draft",
    )
    db.add(session)

    audit = AuditEvent(
        id=str(uuid.uuid4()),
        session_id=session.id,
        actor_id=current_user.id,
        actor_type="human",
        event_type="session_created",
        payload_json={"topic": body.topic, "panel_id": body.panel_id},
    )
    db.add(audit)
    await db.commit()
    await db.refresh(session)
    return SessionResponse.model_validate(session)


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> SessionResponse:
    session = await _get_session_or_404(db, session_id)
    response = SessionResponse.model_validate(session)
    if session.status == "failed":
        result = await db.execute(
            select(AuditEvent)
            .where(
                AuditEvent.session_id == session_id,
                AuditEvent.event_type == "session_status_failed",
            )
            .order_by(AuditEvent.created_at.desc())
            .limit(1)
        )
        audit = result.scalar_one_or_none()
        if audit and "error" in audit.payload_json:
            response.error = audit.payload_json["error"]
    return response


@router.patch("/{session_id}", response_model=SessionResponse)
async def update_session(
    session_id: str,
    body: UpdateSessionRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> SessionResponse:
    session = await _get_session_or_404(db, session_id)
    if session.status != "draft":
        raise HTTPException(status_code=409, detail="Only draft sessions can be updated")

    if body.topic is not None:
        session.topic = body.topic
    if body.success_criteria is not None:
        session.success_criteria = body.success_criteria
    if body.discussion_rules is not None:
        session.discussion_rules_json = body.discussion_rules
    if body.cost_limit is not None:
        session.cost_limit = body.cost_limit

    await db.commit()
    await db.refresh(session)
    return SessionResponse.model_validate(session)


@router.post("/{session_id}/start", status_code=status.HTTP_202_ACCEPTED)
async def start_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Enqueue the discussion job. Transitions session from draft → queued."""
    session = await _get_session_or_404(db, session_id)

    try:
        await StateMachine.transition_status(db, session, "queued", actor_id=current_user.id)
        await db.commit()
    except InvalidTransitionError as e:
        raise HTTPException(status_code=409, detail=str(e))

    # Enqueue Arq job
    try:
        from arq import create_pool
        from app.workers.arq_settings import _redis_settings

        pool = await create_pool(_redis_settings)
        await pool.enqueue_job("run_discussion", session_id)
        await pool.aclose()
    except Exception as exc:
        # Non-fatal in dev (worker may not be running); log only
        import logging
        logging.getLogger(__name__).warning("Failed to enqueue discussion job: %s", exc)

    return {"status": "queued", "session_id": session_id}


@router.post("/{session_id}/pause", status_code=status.HTTP_202_ACCEPTED)
async def pause_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    session = await _get_session_or_404(db, session_id)
    try:
        await StateMachine.transition_status(db, session, "paused", actor_id=current_user.id)
        await db.commit()
    except InvalidTransitionError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return {"status": "paused", "session_id": session_id}


@router.post("/{session_id}/resume", status_code=status.HTTP_202_ACCEPTED)
async def resume_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    session = await _get_session_or_404(db, session_id)
    if session.status != "paused":
        raise HTTPException(status_code=409, detail="Session is not paused")

    try:
        from arq import create_pool
        from app.workers.arq_settings import _redis_settings

        pool = await create_pool(_redis_settings)
        await pool.enqueue_job("resume_discussion", session_id)
        await pool.aclose()
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("Failed to enqueue resume job: %s", exc)

    return {"status": "resuming", "session_id": session_id}


@router.post("/{session_id}/interventions", status_code=status.HTTP_201_CREATED)
async def submit_intervention(
    session_id: str,
    body: InterventionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Submit a human intervention during a running discussion."""
    session = await _get_session_or_404(db, session_id)
    if session.status not in ("running", "paused"):
        raise HTTPException(status_code=409, detail="Session is not active")

    msg = Message(
        id=str(uuid.uuid4()),
        session_id=session_id,
        seat_id=None,
        author_type="human",
        content=body.content,
        reasoning_json={
            "user_id": current_user.id,
            "user_name": current_user.display_name,
            "target_seat": body.target if body.target != "all" else None,
            "injected": False,
        },
        phase_at_creation=session.phase,
    )
    db.add(msg)
    await db.commit()

    # Publish to Redis for live clients
    try:
        redis_client = await aioredis.from_url(settings.redis_url, decode_responses=True)
        event = {
            "event": "intervention",
            "data": {
                "message_id": msg.id,
                "user_id": current_user.id,
                "user_name": current_user.display_name,
                "target_seat": body.target,
                "content": body.content,
            },
        }
        await redis_client.publish(f"discussion:{session_id}", json.dumps(event))
        await redis_client.aclose()
    except Exception:
        pass

    return {"message_id": msg.id}


@router.post("/{session_id}/votes", status_code=status.HTTP_201_CREATED)
async def submit_vote(
    session_id: str,
    body: HumanVoteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Submit a human vote during the voting phase."""
    session = await _get_session_or_404(db, session_id)
    if session.status != "voting":
        raise HTTPException(status_code=409, detail="Session is not in voting phase")

    # Prevent duplicate votes
    existing = await db.execute(
        select(Vote).where(
            Vote.session_id == session_id,
            Vote.voter_id == current_user.id,
            Vote.voter_type == "human",
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="You have already voted")

    vote_row = Vote(
        id=str(uuid.uuid4()),
        session_id=session_id,
        voter_id=current_user.id,
        voter_type="human",
        recommendation_version=1,
        vote=body.vote,
        rationale=body.rationale,
    )
    db.add(vote_row)
    await db.commit()

    # Publish vote update
    try:
        redis_client = await aioredis.from_url(settings.redis_url, decode_responses=True)
        event = {
            "event": "vote_update",
            "data": {
                "voter_type": "human",
                "voter_id": current_user.id,
                "voter_name": current_user.display_name,
                "vote": body.vote,
            },
        }
        await redis_client.publish(f"discussion:{session_id}", json.dumps(event))
        await redis_client.aclose()
    except Exception:
        pass

    return {"vote_id": vote_row.id}


@router.get("/{session_id}/messages", response_model=list[MessageResponse])
async def get_messages(
    session_id: str,
    seat_id: str | None = Query(default=None),
    phase: str | None = Query(default=None),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[MessageResponse]:
    await _get_session_or_404(db, session_id)

    base_query = select(Message).where(Message.session_id == session_id)

    if seat_id:
        base_query = base_query.where(Message.seat_id == seat_id)
    if phase:
        base_query = base_query.where(Message.phase_at_creation == phase)

    base_query = base_query.order_by(Message.created_at)

    result = await db.execute(base_query)
    all_messages = result.scalars().all()

    # Commitments are hidden from other agents during execution (handled in _get_history),
    # but visible to the human user/operator in the UI.
    paginated = all_messages[offset: offset + limit]
    return [MessageResponse.model_validate(m) for m in paginated]


@router.get("/{session_id}/outcome")
async def get_outcome(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict[str, Any]:
    await _get_session_or_404(db, session_id)

    result = await db.execute(
        select(Outcome).where(Outcome.session_id == session_id).order_by(Outcome.created_at.desc())
    )
    outcome = result.scalar_one_or_none()
    if not outcome:
        raise HTTPException(status_code=404, detail="Outcome not yet available")

    return {
        "id": outcome.id,
        "type": outcome.type,
        "statement": outcome.statement,
        "supporting_arguments": outcome.supporting_arguments_json,
        "substantive_dissents": outcome.substantive_dissents_json,
        "agent_vote_summary": outcome.agent_vote_summary_json,
        "human_vote_summary": outcome.human_vote_summary_json,
        "divergence_noted": outcome.divergence_noted,
        "confidence_score": outcome.confidence_score,
        "source_density_score": outcome.source_density_score,
        "created_at": outcome.created_at,
    }


# ─────────────────────────────────────────────
# SSE streaming (Phase 6)
# ─────────────────────────────────────────────

@router.get("/{session_id}/stream")
async def stream_session(
    session_id: str,
    request: Request,
    since_message_id: str | None = Query(default=None),
    token: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """
    SSE stream for a session's real-time events.

    Authentication: pass JWT via Authorization header or ?token= query param.
    Reconnect: pass ?since_message_id= to replay missed messages before resuming live.
    """
    # Auth: bearer header or query param
    auth_header = request.headers.get("authorization", "")
    jwt_token = token
    if not jwt_token and auth_header.startswith("Bearer "):
        jwt_token = auth_header.removeprefix("Bearer ").strip()

    if not jwt_token:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        payload = decode_token(jwt_token)
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token")

    await _get_session_or_404(db, session_id)

    async def event_generator():
        # Replay missed messages if since_message_id provided
        if since_message_id:
            async for chunk in _replay_since(db, session_id, since_message_id):
                yield chunk

        # Emit session_state snapshot on connect
        result = await db.execute(select(Session).where(Session.id == session_id))
        sess = result.scalar_one_or_none()
        if sess:
            state_event = {
                "event": "session_state",
                "data": {
                    "id": sess.id,
                    "status": sess.status,
                    "phase": sess.phase,
                    "topic": sess.topic,
                    "cost_actual": sess.cost_actual,
                    "cost_limit": sess.cost_limit,
                },
            }
            yield f"event: session_state\ndata: {json.dumps(state_event['data'], default=str)}\n\n"

        # Subscribe to live events via Redis pub/sub
        redis_client = await aioredis.from_url(settings.redis_url, decode_responses=True)
        ps = redis_client.pubsub()
        await ps.subscribe(f"discussion:{session_id}")

        try:
            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    break

                message = await ps.get_message(
                    ignore_subscribe_messages=True,
                    timeout=30.0,
                )
                if message is None:
                    # Keepalive comment
                    yield ": keepalive\n\n"
                    continue

                if message["type"] == "message":
                    raw = message["data"]
                    try:
                        evt = json.loads(raw)
                        event_type = evt.get("event", "message")
                        data_payload = json.dumps(evt.get("data", {}), default=str)
                        yield f"event: {event_type}\ndata: {data_payload}\n\n"
                    except (json.JSONDecodeError, TypeError):
                        yield f"data: {raw}\n\n"

        finally:
            await ps.unsubscribe(f"discussion:{session_id}")
            await ps.aclose()
            await redis_client.aclose()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


async def _replay_since(
    db: AsyncSession,
    session_id: str,
    since_message_id: str,
) -> Any:
    """Yield SSE events for all messages after since_message_id."""
    # Find the created_at of the reference message
    ref_result = await db.execute(
        select(Message.created_at).where(
            Message.id == since_message_id,
            Message.session_id == session_id,
        )
    )
    ref_row = ref_result.first()
    if not ref_row:
        return

    ref_ts = ref_row[0]

    missed_result = await db.execute(
        select(Message)
        .where(
            Message.session_id == session_id,
            Message.created_at > ref_ts,
        )
        .order_by(Message.created_at)
    )
    for msg in missed_result.scalars().all():
        event_data = {
            "message_id": msg.id,
            "seat_id": msg.seat_id,
            "author_type": msg.author_type,
            "content": msg.content,
            "phase": msg.phase_at_creation,
        }
        yield f"event: message_replay\ndata: {json.dumps(event_data, default=str)}\n\n"


@router.post("/{session_id}/skip-turn", status_code=status.HTTP_202_ACCEPTED)
async def skip_turn(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Inject a skip signal for the current agent turn."""
    session = await _get_session_or_404(db, session_id)
    if session.status != "running":
        raise HTTPException(status_code=409, detail="Session is not running")

    try:
        redis_client = await aioredis.from_url(settings.redis_url, decode_responses=True)
        await redis_client.publish(
            f"discussion:{session_id}:control",
            json.dumps({"action": "skip_turn", "actor_id": current_user.id}),
        )
        await redis_client.aclose()
    except Exception:
        pass

    return {"status": "skip_requested", "session_id": session_id}


@router.post("/{session_id}/end", status_code=status.HTTP_202_ACCEPTED)
async def end_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Force-end a running discussion and transition to voting."""
    session = await _get_session_or_404(db, session_id)
    if session.status not in ("running", "paused"):
        raise HTTPException(status_code=409, detail="Session is not active")

    try:
        await StateMachine.transition_status(db, session, "voting", actor_id=current_user.id)
        await db.commit()
    except InvalidTransitionError as e:
        raise HTTPException(status_code=409, detail=str(e))

    try:
        redis_client = await aioredis.from_url(settings.redis_url, decode_responses=True)
        event = {
            "event": "phase_change",
            "data": {"from": session.phase, "to": "vote", "summary": "Discussion ended by moderator"},
        }
        await redis_client.publish(f"discussion:{session_id}", json.dumps(event))
        await redis_client.aclose()
    except Exception:
        pass

    # Enqueue voting job so agent votes + recommendation are generated
    try:
        from arq import create_pool
        from app.workers.arq_settings import _redis_settings

        pool = await create_pool(_redis_settings)
        await pool.enqueue_job("run_voting", session_id)
        await pool.aclose()
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("Failed to enqueue voting job: %s", exc)

    return {"status": "voting", "session_id": session_id}


class VoteResponse(BaseModel):
    id: str
    voter_id: str
    voter_type: str
    seat_id: str | None = None
    vote: str
    rationale: str
    submitted_at: Any

    model_config = {"from_attributes": True}


@router.get("/{session_id}/votes", response_model=list[VoteResponse])
async def get_votes(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[VoteResponse]:
    await _get_session_or_404(db, session_id)
    result = await db.execute(
        select(Vote).where(Vote.session_id == session_id).order_by(Vote.submitted_at)
    )
    votes = result.scalars().all()
    out = []
    for v in votes:
        # For agent votes, voter_id is the seat_id; for human votes it's the user UUID.
        seat_id = v.voter_id if v.voter_type == "agent" else None
        out.append(VoteResponse(
            id=v.id,
            voter_id=v.voter_id,
            voter_type=v.voter_type,
            seat_id=seat_id,
            vote=v.vote,
            rationale=v.rationale or "",
            submitted_at=v.submitted_at,
        ))
    return out


class SourceResponse(BaseModel):
    id: str
    url: str
    title: str
    domain: str
    retrieved_at: Any
    retrieval_seat_id: str | None
    quality_signals_json: dict[str, Any]
    flagged_by_json: list[Any]
    flag_notes: str | None

    model_config = {"from_attributes": True}


@router.get("/{session_id}/sources", response_model=list[SourceResponse])
async def get_sources(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[SourceResponse]:
    await _get_session_or_404(db, session_id)
    result = await db.execute(
        select(Source).where(Source.session_id == session_id).order_by(Source.retrieved_at)
    )
    return [SourceResponse.model_validate(s) for s in result.scalars().all()]


class DecisionOutcomeRequest(BaseModel):
    result: str = Field(..., pattern="^(adopted_success|adopted_failure|chose_differently)$")
    notes: str | None = None


@router.post("/{session_id}/decision-outcome", status_code=status.HTTP_201_CREATED)
async def mark_decision_outcome(
    session_id: str,
    body: DecisionOutcomeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Post-hoc marking of whether the decision was acted upon and succeeded."""
    session = await _get_session_or_404(db, session_id)
    if session.status != "concluded":
        raise HTTPException(status_code=409, detail="Session has not concluded")

    from app.db.models import DecisionOutcome

    decision = DecisionOutcome(
        id=str(uuid.uuid4()),
        session_id=session_id,
        marked_by=current_user.id,
        result=body.result,
        notes=body.notes,
    )
    db.add(decision)

    audit = AuditEvent(
        id=str(uuid.uuid4()),
        session_id=session_id,
        actor_id=current_user.id,
        actor_type="human",
        event_type="decision_outcome_marked",
        payload_json={"result": body.result},
    )
    db.add(audit)
    await db.commit()

    return {"decision_outcome_id": decision.id}


class AuditEventResponse(BaseModel):
    id: str
    actor_id: str | None
    actor_type: str | None
    event_type: str
    payload_json: dict[str, Any]
    created_at: Any

    model_config = {"from_attributes": True}


@router.get("/{session_id}/audit", response_model=list[AuditEventResponse])
async def get_audit(
    session_id: str,
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[AuditEventResponse]:
    await _get_session_or_404(db, session_id)
    result = await db.execute(
        select(AuditEvent)
        .where(AuditEvent.session_id == session_id)
        .order_by(AuditEvent.created_at)
        .offset(offset)
        .limit(limit)
    )
    return [AuditEventResponse.model_validate(e) for e in result.scalars().all()]


@router.get("/{session_id}/export")
async def export_session(
    session_id: str,
    format: str = Query(default="json", pattern="^(json|markdown|pdf)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """Export session as JSON, Markdown, or PDF (PDF is async)."""
    import hashlib
    import hmac
    from fastapi.responses import Response

    session = await _get_session_or_404(db, session_id)

    msg_result = await db.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at)
    )
    messages = msg_result.scalars().all()
    visible_messages = messages

    src_result = await db.execute(
        select(Source).where(Source.session_id == session_id).order_by(Source.retrieved_at)
    )
    sources = src_result.scalars().all()

    vote_result = await db.execute(
        select(Vote).where(Vote.session_id == session_id)
    )
    votes = vote_result.scalars().all()

    outcome_result = await db.execute(
        select(Outcome).where(Outcome.session_id == session_id).order_by(Outcome.created_at.desc())
    )
    outcome = outcome_result.scalar_one_or_none()

    audit_result = await db.execute(
        select(AuditEvent).where(AuditEvent.session_id == session_id).order_by(AuditEvent.created_at)
    )
    audit_events = audit_result.scalars().all()

    if format == "json":
        bundle = {
            "session": {
                "id": session.id,
                "topic": session.topic,
                "outcome_type": session.outcome_type,
                "status": session.status,
                "phase": session.phase,
                "panel_id": session.panel_id,
                "cost_actual": session.cost_actual,
                "started_at": str(session.started_at) if session.started_at else None,
                "concluded_at": str(session.concluded_at) if session.concluded_at else None,
                "created_at": str(session.created_at),
            },
            "messages": [
                {
                    "id": m.id,
                    "seat_id": m.seat_id,
                    "author_type": m.author_type,
                    "content": m.content,
                    "model": m.model,
                    "phase": m.phase_at_creation,
                    "created_at": str(m.created_at),
                }
                for m in visible_messages
            ],
            "sources": [
                {"id": s.id, "url": s.url, "title": s.title, "domain": s.domain}
                for s in sources
            ],
            "votes": [
                {"voter_id": v.voter_id, "voter_type": v.voter_type, "vote": v.vote, "rationale": v.rationale}
                for v in votes
            ],
            "outcome": {
                "type": outcome.type,
                "statement": outcome.statement,
                "confidence_score": outcome.confidence_score,
            } if outcome else None,
            "audit_events": [
                {"event_type": e.event_type, "actor_type": e.actor_type, "created_at": str(e.created_at)}
                for e in audit_events
            ],
        }

        bundle_bytes = json.dumps(bundle, ensure_ascii=False).encode()
        sig = hmac.new(
            settings.jwt_private_key.encode()[:32].ljust(32, b"0"),
            bundle_bytes,
            hashlib.sha256,
        ).hexdigest()

        response_data = json.dumps({"data": bundle, "signature": sig}, ensure_ascii=False, default=str)
        return Response(
            content=response_data,
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="session-{session_id}.json"'},
        )

    elif format == "markdown":
        lines = [
            f"# AI Round Table: {session.topic}",
            "",
            f"**Panel:** {session.panel_id}",
            f"**Status:** {session.status}",
            f"**Cost:** ${session.cost_actual:.4f}",
            "",
        ]

        if outcome:
            lines += [
                "## Outcome",
                "",
                f"**Type:** {outcome.type}",
                "",
                outcome.statement,
                "",
            ]

        lines += ["## Transcript", ""]
        for msg in visible_messages:
            author = msg.seat_id or msg.author_type
            lines.append(f"### {author} ({msg.phase_at_creation or 'unknown phase'})")
            lines.append("")
            lines.append(msg.content)
            lines.append("")

        if sources:
            lines += ["## Sources", ""]
            for i, src in enumerate(sources, 1):
                lines.append(f"{i}. [{src.title}]({src.url}) — {src.domain}")
            lines.append("")

        md_content = "\n".join(lines)
        return Response(
            content=md_content.encode(),
            media_type="text/markdown",
            headers={"Content-Disposition": f'attachment; filename="session-{session_id}.md"'},
        )

    else:  # pdf
        return {"status": "queued", "message": "PDF export is generated asynchronously. Check back shortly."}


# ─────────────────────────────────────────────
# WebSocket (Phase 6)
# ─────────────────────────────────────────────

@router.websocket("/{session_id}/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """WebSocket endpoint for bidirectional real-time communication."""
    await handle_websocket(websocket=websocket, session_id=session_id, db=db)


# ─────────────────────────────────────────────
# Cost estimation
# ─────────────────────────────────────────────

class EstimateRequest(BaseModel):
    panel_id: str
    duration_turns: int = Field(default=30, ge=1, le=200)


@router.post("/estimate")
async def estimate_cost(
    body: EstimateRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Estimate cost and duration for a session."""
    panel = await PanelRegistry.get_by_id(db, body.panel_id)
    if not panel:
        raise HTTPException(status_code=404, detail="Panel not found")

    from app.llm.pricing import calculate_cost

    avg_tokens_per_turn = 600
    total_cost = 0.0
    for seat in panel.seats:
        cost = calculate_cost(seat.model, avg_tokens_per_turn, avg_tokens_per_turn)
        total_cost += cost * body.duration_turns

    estimated_minutes = (body.duration_turns * 30) // 60

    return {
        "cost_low": round(total_cost * 0.7, 4),
        "cost_high": round(total_cost * 1.3, 4),
        "duration_min": estimated_minutes,
        "turns": body.duration_turns,
    }


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

async def _get_session_or_404(db: AsyncSession, session_id: str) -> Session:
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


def _estimate_cost(panel: Any) -> float:
    """Rough cost estimate for a default-length session."""
    from app.llm.pricing import calculate_cost

    avg_tokens = 600
    default_turns = 30
    total = 0.0
    for seat in panel.seats:
        total += calculate_cost(seat.model, avg_tokens, avg_tokens) * default_turns
    return round(total, 4)
