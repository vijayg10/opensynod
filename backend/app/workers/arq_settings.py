import urllib.parse

import redis.asyncio as aioredis
from arq.connections import RedisSettings

from app.core.config import get_settings
from app.workers.discussion_worker import inject_intervention, resume_discussion, run_discussion, run_voting

settings = get_settings()

_parsed = urllib.parse.urlparse(settings.redis_url)
_redis_settings = RedisSettings(
    host=_parsed.hostname or "localhost",
    port=_parsed.port or 6379,
    database=int(_parsed.path.lstrip("/") or "0"),
    password=_parsed.password,
)


async def startup(ctx: dict) -> None:
    """Initialize shared resources for each worker process."""
    from app.db.session import AsyncSessionLocal

    ctx["session_factory"] = AsyncSessionLocal
    ctx["pubsub_redis"] = await aioredis.from_url(
        settings.redis_url,
        decode_responses=True,
    )


async def shutdown(ctx: dict) -> None:
    """Clean up shared resources on worker shutdown."""
    if "pubsub_redis" in ctx:
        await ctx["pubsub_redis"].aclose()


class WorkerSettings:
    redis_settings = _redis_settings
    functions = [run_discussion, resume_discussion, inject_intervention, run_voting]
    on_startup = startup
    on_shutdown = shutdown
    max_jobs = 10
    job_timeout = 3600
    queue_name = "arq:queue"
