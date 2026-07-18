"""
Console access endpoint. The frontend's `console_url` (returned on a running
VMSession, see app/api/v1/routers/vms.py) points here:
    wss://<host>/console/<websocket_token>

The token is an opaque, unguessable per-session value generated in
`vm_lifecycle.provision_vm` — knowing it is what authorizes the connection
(not a JWT bearer header, since the browser's native WebSocket API can't set
custom headers). It is scoped to exactly one session, is only valid while
that session is `running`, and is invalidated the moment the VM stops
(overwritten to a new value on the *next* provision — a stopped session's
old token no longer matches any `running` row).
"""
from fastapi import APIRouter, WebSocket
from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import AsyncSessionLocal
from app.models.vm_session import VMSession, VMState
from app.services.console_proxy import relay

router = APIRouter(tags=["console"])
settings = get_settings()


@router.websocket("/console/{token}")
async def console_ws(websocket: WebSocket, token: str):
    async with AsyncSessionLocal() as db:
        session = (
            await db.execute(
                select(VMSession).where(
                    VMSession.websocket_token == token, VMSession.state == VMState.running
                )
            )
        ).scalar_one_or_none()

    if session is None or session.vnc_port is None:
        await websocket.close(code=4001)
        return

    await websocket.accept(subprotocol="binary")
    await relay(websocket, settings.vm_vnc_host, session.vnc_port)
