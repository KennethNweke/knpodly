"""
QCOW2 overlay disk management.

Overlays are created with `qemu-img create -f qcow2 -b <base> -F qcow2
<overlay>`, which makes them copy-on-write children of the immutable master
image — the master is opened read-only by QEMU and is never modified.
Deleting the overlay file after shutdown fully reclaims the session's disk
delta; the master image size never changes.

VNC port allocation is backed by a Redis SET (`_VNC_PORT_REDIS_KEY`), not an
in-process counter — with two `vm-worker` replicas (see
docker-compose.prod.yml), an in-memory counter would let both replicas hand
out the same port to two different sessions. Using Redis as the shared
source of truth for "which ports are currently in use" fixes that; the
SADD/SREM operations are atomic so concurrent allocations never collide.
"""
from __future__ import annotations

import asyncio
import os

import redis.asyncio as redis

from app.core.config import get_settings

settings = get_settings()

# VNC ports allocated to running sessions, cycling through this range and
# reused once a session ends (see release_vnc_port). Kept well clear of
# libvirt's own default autoport range and other common services.
_VNC_PORT_MIN = 5900
_VNC_PORT_MAX = 6900
_VNC_PORT_REDIS_KEY = "knpodly:vnc_ports:in_use"  # Redis SET of ports currently allocated


async def create_overlay(*, base_image_path: str, session_id: str) -> str:
    os.makedirs(settings.vm_overlay_path, exist_ok=True)
    overlay_path = os.path.join(settings.vm_overlay_path, f"{session_id}.qcow2")

    proc = await asyncio.create_subprocess_exec(
        "qemu-img", "create", "-f", "qcow2", "-b", base_image_path, "-F", "qcow2", overlay_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"qemu-img overlay creation failed: {stderr.decode(errors='replace')}")
    return overlay_path


async def destroy_overlay(overlay_path: str) -> None:
    """Idempotent: missing file is not an error (already cleaned up)."""
    try:
        os.remove(overlay_path)
    except FileNotFoundError:
        pass


async def allocate_vnc_port() -> int:
    """Atomically claims the lowest free port in [_VNC_PORT_MIN, _VNC_PORT_MAX)
    across all vm-worker replicas. Raises RuntimeError if the range is
    exhausted (i.e. VM_MAX_CONCURRENT_TOTAL is set higher than the port
    range can support — widen _VNC_PORT_MAX or lower the concurrency cap)."""
    r = redis.from_url(settings.redis_url, decode_responses=True)
    try:
        in_use = {int(p) for p in await r.smembers(_VNC_PORT_REDIS_KEY)}
        for port in range(_VNC_PORT_MIN, _VNC_PORT_MAX):
            if port in in_use:
                continue
            # SADD returns 0 if the member already existed — i.e. another
            # worker claimed this exact port between our SMEMBERS read and
            # now. Loop to the next candidate rather than trusting our
            # stale snapshot.
            added = await r.sadd(_VNC_PORT_REDIS_KEY, port)
            if added:
                return port
        raise RuntimeError(
            f"No free VNC ports in range {_VNC_PORT_MIN}-{_VNC_PORT_MAX}; "
            "increase the range or lower VM_MAX_CONCURRENT_TOTAL."
        )
    finally:
        await r.close()


async def release_vnc_port(port: int) -> None:
    """Called on VM teardown so the port can be reused by a future session."""
    r = redis.from_url(settings.redis_url, decode_responses=True)
    try:
        await r.srem(_VNC_PORT_REDIS_KEY, port)
    finally:
        await r.close()
