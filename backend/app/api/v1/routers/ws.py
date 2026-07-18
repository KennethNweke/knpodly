"""
WebSocket endpoints for real-time dashboard updates and console activity
heartbeats.

Dashboard broadcasting is backed by Redis pub/sub (see
app/services/redis_bus.py) so it works correctly across multiple backend
replicas: a client connected to replica A still receives events published
by replica B's vm-worker or scheduler process. `ConnectionManager` here is
purely the in-process fan-out to this replica's own open sockets; the bus
is what feeds it.
"""
import logging
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.db.session import AsyncSessionLocal
from app.models.vm_session import VMSession
from app.services import vm_lifecycle

router = APIRouter(tags=["websocket"])
logger = logging.getLogger("knpodly.ws")


class ConnectionManager:
    def __init__(self):
        self.active: dict[str, list[WebSocket]] = {}

    async def connect(self, channel: str, ws: WebSocket):
        await ws.accept()
        self.active.setdefault(channel, []).append(ws)

    def disconnect(self, channel: str, ws: WebSocket):
        if channel in self.active and ws in self.active[channel]:
            self.active[channel].remove(ws)

    async def broadcast(self, channel: str, message: dict):
        dead = []
        for ws in self.active.get(channel, []):
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(channel, ws)


manager = ConnectionManager()


@router.websocket("/ws/dashboard")
async def dashboard_ws(websocket: WebSocket):
    """Streams host stats / VM state changes / maintenance alerts to lecturer
    dashboards. This endpoint itself never produces events — it just holds
    the connection open and receives pushes forwarded from Redis via
    `redis_bus.init_redis_bus()` -> `manager.broadcast("dashboard", ...)`."""
    await manager.connect("dashboard", websocket)
    try:
        while True:
            # Client doesn't need to send anything; receive_text() just
            # keeps the connection loop alive until disconnect.
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect("dashboard", websocket)


@router.websocket("/ws/vm/{session_id}/activity")
async def vm_activity_ws(websocket: WebSocket, session_id: str):
    """Lightweight heartbeat channel the frontend pings on keyboard/mouse/focus
    events, used for idle-timeout detection (see docs/architecture.md).

    NOTE ON AUTH: unlike REST endpoints, this doesn't verify a JWT bearer
    token (browsers can't set custom headers on native WebSocket connects).
    It only resets the idle timer for the given session id and has no
    read/write access to anything else, so the worst case of a forged
    session_id is "someone else's idle timer gets reset" — low severity,
    but production deployments wanting stricter guarantees should pass a
    short-lived `?token=` query param here and validate it against
    `VMSession.websocket_token`.
    """
    await websocket.accept()
    try:
        session_uuid = uuid.UUID(session_id)
    except ValueError:
        await websocket.close(code=4000)
        return

    try:
        while True:
            await websocket.receive_text()
            async with AsyncSessionLocal() as db:
                session = (
                    await db.get(VMSession, session_uuid)
                )
                if session is not None:
                    await vm_lifecycle.record_activity(db, session=session)
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("Error handling activity heartbeat for session %s", session_id)
