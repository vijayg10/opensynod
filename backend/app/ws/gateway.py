"""WebSocket gateway: handles bidirectional real-time communication."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

import redis.asyncio as aioredis
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.db.models import Message, Session, Source, User, Vote
from app.ws.redis_pubsub import PresenceManager, get_redis_client

logger = logging.getLogger(__name__)


async def _authenticate_ws(token: str, db: AsyncSession) -> User | None:
    """Validate a JWT token and return the corresponding user."""
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            return None
        user_id = payload.get("sub")
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user and user.is_active:
            return user
        return None
    except (ValueError, Exception):
        return None


async def _get_session_state(session_id: str, db: AsyncSession) -> dict[str, Any] | None:
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        return None
    return {
        "id": session.id,
        "status": session.status,
        "phase": session.phase,
        "topic": session.topic,
        "cost_actual": session.cost_actual,
        "cost_limit": session.cost_limit,
    }


async def handle_websocket(
    websocket: WebSocket,
    session_id: str,
    db: AsyncSession,
) -> None:
    """Handle a WebSocket connection for a discussion session."""
    await websocket.accept()

    redis_client: aioredis.Redis | None = None
    user: User | None = None
    presence: PresenceManager | None = None

    try:
        # Step 1: Authentication handshake
        auth_data = await websocket.receive_json()
        if auth_data.get("type") != "auth":
            await websocket.send_json({"type": "error", "code": "AUTH_REQUIRED", "message": "First message must be auth"})
            await websocket.close(code=4001)
            return

        user = await _authenticate_ws(auth_data.get("token", ""), db)
        if not user:
            await websocket.send_json({"type": "error", "code": "AUTH_FAILED", "message": "Invalid token"})
            await websocket.close(code=4001)
            return

        # Step 2: Verify session exists
        session_state = await _get_session_state(session_id, db)
        if not session_state:
            await websocket.send_json({"type": "error", "code": "SESSION_NOT_FOUND", "message": "Session not found"})
            await websocket.close(code=4004)
            return

        # Step 3: Send auth_ok with session state
        await websocket.send_json({
            "type": "auth_ok",
            "user_id": user.id,
            "display_name": user.display_name,
            "session_state": session_state,
        })

        # Step 4: Register presence
        redis_client = await get_redis_client()
        presence = PresenceManager(redis_client)
        await presence.register(
            session_id=session_id,
            user_id=user.id,
            display_name=user.display_name,
            avatar_url=user.avatar_url,
        )

        # Step 5: Handle messages
        while True:
            try:
                data = await websocket.receive_json()
            except (WebSocketDisconnect, RuntimeError):
                break

            msg_type = data.get("type")

            if msg_type == "presence_ping":
                await presence.refresh(session_id, user.id)

            elif msg_type == "intervention":
                await _handle_intervention(
                    websocket=websocket,
                    session_id=session_id,
                    user=user,
                    data=data,
                    db=db,
                    redis_client=redis_client,
                )

            elif msg_type == "vote":
                await _handle_vote(
                    session_id=session_id,
                    user=user,
                    data=data,
                    db=db,
                    redis_client=redis_client,
                )

            elif msg_type == "flag_source":
                await _handle_flag_source(
                    session_id=session_id,
                    data=data,
                    db=db,
                )

            else:
                await websocket.send_json({
                    "type": "error",
                    "code": "UNKNOWN_MESSAGE_TYPE",
                    "message": f"Unknown message type: {msg_type}",
                })

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.exception("WebSocket error for session %s: %s", session_id, exc)
    finally:
        if presence and user:
            try:
                await presence.deregister(session_id, user.id)
            except Exception:
                pass
        if redis_client:
            try:
                await redis_client.aclose()
            except Exception:
                pass


async def _handle_intervention(
    websocket: WebSocket,
    session_id: str,
    user: User,
    data: dict[str, Any],
    db: AsyncSession,
    redis_client: aioredis.Redis,
) -> None:
    """Persist a human intervention and publish it to the discussion channel."""
    content = data.get("content", "").strip()
    target = data.get("target", "all")
    if not content:
        return

    msg = Message(
        id=str(uuid.uuid4()),
        session_id=session_id,
        seat_id=None,
        author_type="human",
        content=content,
        reasoning_json={
            "user_id": user.id,
            "user_name": user.display_name,
            "target_seat": target if target != "all" else None,
            "injected": False,
        },
    )
    db.add(msg)
    await db.commit()

    event = {
        "event": "intervention",
        "data": {
            "message_id": msg.id,
            "user_id": user.id,
            "user_name": user.display_name,
            "target_seat": target,
            "content": content,
        },
    }
    await redis_client.publish(f"discussion:{session_id}", json.dumps(event, default=str))


async def _handle_vote(
    session_id: str,
    user: User,
    data: dict[str, Any],
    db: AsyncSession,
    redis_client: aioredis.Redis,
) -> None:
    """Record a human vote during the voting phase."""
    vote_value = data.get("vote", "").lower()
    if vote_value not in ("yes", "no", "abstain"):
        return
    rationale = data.get("rationale", "")

    vote_row = Vote(
        id=str(uuid.uuid4()),
        session_id=session_id,
        voter_id=user.id,
        voter_type="human",
        recommendation_version=1,
        vote=vote_value,
        rationale=rationale,
    )
    db.add(vote_row)
    await db.commit()

    event = {
        "event": "vote_update",
        "data": {
            "voter_type": "human",
            "voter_id": user.id,
            "voter_name": user.display_name,
            "vote": vote_value,
        },
    }
    await redis_client.publish(f"discussion:{session_id}", json.dumps(event, default=str))


async def _handle_flag_source(
    session_id: str,
    data: dict[str, Any],
    db: AsyncSession,
) -> None:
    """Flag a source as potentially unreliable."""
    source_id = data.get("source_id", "")
    notes = data.get("notes", "")
    if not source_id:
        return

    result = await db.execute(select(Source).where(Source.id == source_id, Source.session_id == session_id))
    source = result.scalar_one_or_none()
    if not source:
        return

    flagged_by = list(source.flagged_by_json or [])
    flagged_by.append({"source_id": source_id, "notes": notes, "flagged_at": datetime.now(timezone.utc).isoformat()})

    # Sources are not append-only so we can update them
    source.flagged_by_json = flagged_by
    if notes:
        source.flag_notes = notes
    await db.commit()
