"""
Shared arq Redis pool for enqueueing background jobs from the API process
(as opposed to app/workers/vm_worker.py, which is the consumer side).

Created once at app startup and reused across requests via FastAPI's
dependency system / app.state, rather than opening a new Redis connection
per request.
"""
from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

from app.core.config import get_settings

settings = get_settings()

_pool: ArqRedis | None = None


async def init_arq_pool() -> ArqRedis:
    global _pool
    if _pool is None:
        _pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    return _pool


async def close_arq_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def get_arq_pool() -> ArqRedis:
    if _pool is None:
        raise RuntimeError("arq pool not initialized — is the app lifespan running?")
    return _pool
