"""
Simple fixed-window rate limiter backed by Redis, used to throttle
brute-force login attempts. Keyed by client IP + attempted username, so one
malicious IP hammering many usernames and one malicious actor spraying a
single username from many IPs are both caught, without one legitimate
user's mistyped password locking out the whole building's shared IP.
"""
from __future__ import annotations

import redis.asyncio as redis
from fastapi import HTTPException, status

from app.core.config import get_settings

settings = get_settings()

_WINDOW_SECONDS = 300  # 5 minutes
_MAX_ATTEMPTS = 10


async def check_login_rate_limit(*, ip_address: str, username: str) -> None:
    r = redis.from_url(settings.redis_url, decode_responses=True)
    try:
        key = f"knpodly:login_attempts:{ip_address}:{username.lower()}"
        attempts = await r.incr(key)
        if attempts == 1:
            await r.expire(key, _WINDOW_SECONDS)
        if attempts > _MAX_ATTEMPTS:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many login attempts. Please wait a few minutes and try again.",
            )
    finally:
        await r.close()


async def reset_login_rate_limit(*, ip_address: str, username: str) -> None:
    """Called on successful login so a legitimate user who mistyped their
    password a few times isn't left sitting close to the limit."""
    r = redis.from_url(settings.redis_url, decode_responses=True)
    try:
        await r.delete(f"knpodly:login_attempts:{ip_address}:{username.lower()}")
    finally:
        await r.close()
