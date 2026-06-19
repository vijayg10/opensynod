"""Redis pub/sub utilities for the real-time layer."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import redis.asyncio as aioredis

from app.core.config import get_settings

_PRESENCE_TTL = 60  # seconds before a presence entry expires


def _channel(session_id: str) -> str:
    return f"discussion:{session_id}"


def _presence_key(session_id: str) -> str:
    return f"discussion:{session_id}:presence"


async def publish_event(
    redis_client: aioredis.Redis,
    session_id: str,
    event: dict[str, Any],
) -> None:
    """Publish an event to the session's discussion channel."""
    await redis_client.publish(_channel(session_id), json.dumps(event, default=str))


async def get_redis_client(decode_responses: bool = True) -> aioredis.Redis:
    """Create a new async Redis client from settings."""
    settings = get_settings()
    return await aioredis.from_url(settings.redis_url, decode_responses=decode_responses)


class PresenceManager:
    """Manages user presence tracking in Redis."""

    def __init__(self, redis_client: aioredis.Redis) -> None:
        self._redis = redis_client

    async def register(
        self,
        session_id: str,
        user_id: str,
        display_name: str,
        avatar_url: str | None = None,
    ) -> None:
        key = _presence_key(session_id)
        entry = json.dumps({
            "name": display_name,
            "avatar": avatar_url,
            "last_seen_at": datetime.now(timezone.utc).isoformat(),
        })
        await self._redis.hset(key, user_id, entry)
        await self._redis.expire(key, _PRESENCE_TTL * 10)
        await self._publish_presence(session_id)

    async def refresh(self, session_id: str, user_id: str) -> None:
        key = _presence_key(session_id)
        raw = await self._redis.hget(key, user_id)
        if raw:
            entry = json.loads(raw)
            entry["last_seen_at"] = datetime.now(timezone.utc).isoformat()
            await self._redis.hset(key, user_id, json.dumps(entry))
            await self._redis.expire(key, _PRESENCE_TTL * 10)

    async def deregister(self, session_id: str, user_id: str) -> None:
        key = _presence_key(session_id)
        await self._redis.hdel(key, user_id)
        await self._publish_presence(session_id)

    async def get_all(self, session_id: str) -> list[dict[str, Any]]:
        key = _presence_key(session_id)
        raw_map = await self._redis.hgetall(key)
        users: list[dict[str, Any]] = []
        for user_id, raw_value in raw_map.items():
            try:
                entry = json.loads(raw_value)
                entry["user_id"] = user_id
                users.append(entry)
            except (json.JSONDecodeError, TypeError):
                pass
        return users

    async def _publish_presence(self, session_id: str) -> None:
        users = await self.get_all(session_id)
        event = {
            "event": "presence_update",
            "data": {"users": users},
        }
        await self._redis.publish(_channel(session_id), json.dumps(event, default=str))
