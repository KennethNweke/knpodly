"""
Redis pub/sub bus used to fan out real-time events (VM state changes, host
stat updates, maintenance toggles) to every connected `/ws/dashboard` client
— including clients connected to a *different* backend replica than the one
that produced the event. This is what makes the WebSocket layer correct in
a horizontally-scaled deployment (`vm-worker` replicas: 2 in
docker-compose.prod.yml) instead of only working when there's exactly one
backend process.

Flow:
  vm_worker / scheduler  --publish-->  Redis channel "knpodly:dashboard"
                                              |
  every backend replica's `redis_bus_listener()` background task subscribes
  and forwards each message into that replica's in-process
  `ConnectionManager`, which pushes it out over each open WebSocket.
"""
from __future__ import annotations

import asyncio
import json
import logging

import redis.asyncio as redis

from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger("knpodly.redis_bus")

DASHBOARD_CHANNEL = "knpodly:dashboard"

_redis: redis.Redis | None = None
_listener_task: asyncio.Task | None = None


async def init_redis_bus() -> None:
    """Called from the API process's lifespan. Starts a background task that
    forwards Redis pub/sub messages into the in-process WebSocket
    ConnectionManager (see app/api/v1/routers/ws.py)."""
    global _redis, _listener_task
    from app.api.v1.routers.ws import manager  # local import avoids a circular import

    _redis = redis.from_url(settings.redis_url, decode_responses=True)

    async def _listen():
        pubsub = _redis.pubsub()
        await pubsub.subscribe(DASHBOARD_CHANNEL)
        try:
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                try:
                    payload = json.loads(message["data"])
                except json.JSONDecodeError:
                    logger.warning("Dropping malformed dashboard event: %r", message["data"])
                    continue
                await manager.broadcast("dashboard", payload)
        except asyncio.CancelledError:
            pass
        finally:
            await pubsub.unsubscribe(DASHBOARD_CHANNEL)

    _listener_task = asyncio.create_task(_listen())


async def close_redis_bus() -> None:
    global _redis, _listener_task
    if _listener_task is not None:
        _listener_task.cancel()
        _listener_task = None
    if _redis is not None:
        await _redis.close()
        _redis = None


async def publish_event(event_type: str, data: dict) -> None:
    """Called by vm_worker/scheduler (separate processes) to notify all
    connected dashboards. Opens its own short-lived Redis connection since
    those processes don't share the API process's `_redis` handle."""
    r = redis.from_url(settings.redis_url, decode_responses=True)
    try:
        await r.publish(DASHBOARD_CHANNEL, json.dumps({"type": event_type, **data}))
    finally:
        await r.close()
