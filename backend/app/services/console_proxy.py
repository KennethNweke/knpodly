"""
Raw TCP <-> WebSocket relay (a minimal 'websockify') that lets the browser's
noVNC client, which only speaks WebSocket, reach QEMU's VNC server, which
only speaks raw TCP/RFB.

This intentionally does NOT do any RFB protocol parsing — it's a byte-level
pipe in both directions. All session/permission validation happens before
the pipe is opened (see the /console/{token} route in
app/api/v1/routers/console.py): the token has already proven the connecting
user owns a `running` VM session before a single byte is relayed.
"""
from __future__ import annotations

import asyncio
import logging

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger("knpodly.console_proxy")

# Bytes per read; large enough to avoid excessive syscalls for VNC's
# framebuffer updates, small enough to keep latency low for keyboard/mouse
# events flowing the other direction.
CHUNK_SIZE = 65536


async def relay(websocket: WebSocket, vnc_host: str, vnc_port: int) -> None:
    try:
        reader, writer = await asyncio.open_connection(vnc_host, vnc_port)
    except (ConnectionRefusedError, OSError) as e:
        logger.warning("Could not connect to VNC backend %s:%s: %s", vnc_host, vnc_port, e)
        await websocket.close(code=4002)
        return

    async def ws_to_tcp():
        try:
            while True:
                data = await websocket.receive_bytes()
                writer.write(data)
                await writer.drain()
        except WebSocketDisconnect:
            pass
        finally:
            writer.close()

    async def tcp_to_ws():
        try:
            while True:
                data = await reader.read(CHUNK_SIZE)
                if not data:
                    break
                await websocket.send_bytes(data)
        except Exception:
            pass
        finally:
            try:
                await websocket.close()
            except Exception:
                pass

    await asyncio.gather(ws_to_tcp(), tcp_to_ws(), return_exceptions=True)
