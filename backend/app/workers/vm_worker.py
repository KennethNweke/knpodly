"""
arq worker: processes VM provisioning/teardown jobs off the request path.

Run with: arq app.workers.vm_worker.WorkerSettings
(see docker-compose.yml `vm-worker` service)
"""
import logging
import uuid

from arq.connections import RedisSettings
from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import AsyncSessionLocal
from app.models.operating_system import OperatingSystem
from app.models.vm_session import VMSession
from app.services import vm_lifecycle
from app.services.libvirt_client import get_libvirt_client
from app.services.redis_bus import publish_event

settings = get_settings()
logger = logging.getLogger("knpodly.vm_worker")


async def provision_vm(ctx, session_id: str) -> None:
    async with AsyncSessionLocal() as db:
        session = (
            await db.execute(select(VMSession).where(VMSession.id == uuid.UUID(session_id)))
        ).scalar_one_or_none()
        if not session:
            logger.warning("provision_vm: session %s not found (already deleted?)", session_id)
            return
        os_row = (
            await db.execute(
                select(OperatingSystem).where(OperatingSystem.id == session.operating_system_id)
            )
        ).scalar_one()
        libvirt = get_libvirt_client()
        try:
            session = await vm_lifecycle.provision_vm(db, session=session, os_row=os_row, libvirt=libvirt)
        except Exception:
            logger.exception("Provisioning failed for session %s", session_id)
            await publish_event("vm.failed", {"session_id": session_id, "user_id": str(session.user_id)})
            raise
        await publish_event(
            "vm.running",
            {
                "session_id": str(session.id),
                "user_id": str(session.user_id),
                "expires_at": session.expires_at.isoformat() if session.expires_at else None,
            },
        )


async def teardown_vm(ctx, session_id: str, reason: str, force: bool = False) -> None:
    async with AsyncSessionLocal() as db:
        session = (
            await db.execute(select(VMSession).where(VMSession.id == uuid.UUID(session_id)))
        ).scalar_one_or_none()
        if not session:
            return
        libvirt = get_libvirt_client()
        await vm_lifecycle.stop_vm(db, session=session, libvirt=libvirt, reason=reason, force=force)
        await publish_event(
            "vm.stopped", {"session_id": session_id, "user_id": str(session.user_id), "reason": reason}
        )


class WorkerSettings:
    functions = [provision_vm, teardown_vm]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_jobs = 20  # bounds concurrent provisioning; tune against host capacity
