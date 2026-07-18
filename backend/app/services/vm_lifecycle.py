"""
Core VM lifecycle orchestration: launch, stop, force-stop, extend, expire.

This service is intentionally libvirt-call-free at the top level — it
delegates actual hypervisor operations to `BaseLibvirtClient` and disk
operations to `overlay_manager`, so it can be unit tested against the fake
driver and reused unchanged by both the FastAPI request path (for
synchronous validation) and the arq worker (for the actual async
provisioning work, see app/workers/vm_worker.py).

Enforced business rules (from spec):
  - One running VM per student (DB unique index is the source of truth;
    this service checks first for a fast, friendly error).
  - Lecturers may launch multiple VMs.
  - Default session 2h, one extension up to +1h.
  - Master image (base.qcow2) is never written to; only overlays are created
    and destroyed.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.maintenance_window import MaintenanceWindow
from app.models.user import User, UserRole
from app.models.vm_session import VMSession, VMState
from app.models.operating_system import OperatingSystem, OSStatus
from app.services import overlay_manager
from app.services.domain_xml import render_domain_xml
from app.services.libvirt_client import BaseLibvirtClient
from app.services.policy import get_active_policy

settings = get_settings()


class VMLimitExceeded(Exception):
    pass


class OSUnavailable(Exception):
    pass


class MaintenanceActive(Exception):
    pass


async def launch_vm(
    db: AsyncSession,
    *,
    user: User,
    os_slug: str,
    libvirt: BaseLibvirtClient,
) -> VMSession:
    if user.role == UserRole.student:
        maintenance = (
            await db.execute(select(MaintenanceWindow).where(MaintenanceWindow.is_active.is_(True)))
        ).scalars().first()
        if maintenance is not None:
            raise MaintenanceActive(
                maintenance.message or "The lab platform is currently under maintenance. Please try again later."
            )

        existing = await db.execute(
            select(VMSession).where(
                VMSession.user_id == user.id,
                VMSession.state.in_(
                    [VMState.queued, VMState.provisioning, VMState.running, VMState.stopping]
                ),
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise VMLimitExceeded("Students may only run one VM at a time.")

    policy = await get_active_policy(db)

    total_active = (
        await db.execute(
            select(VMSession).where(
                VMSession.state.in_(
                    [VMState.queued, VMState.provisioning, VMState.running, VMState.stopping]
                )
            )
        )
    ).scalars().all()
    if len(total_active) >= policy.max_concurrent_vms_total:
        raise VMLimitExceeded(
            "The lab is at maximum capacity right now. Please try again shortly."
        )

    os_row = (
        await db.execute(select(OperatingSystem).where(OperatingSystem.slug == os_slug))
    ).scalar_one_or_none()
    if os_row is None or os_row.status != OSStatus.available:
        raise OSUnavailable(f"Operating system '{os_slug}' is not available for launch.")

    session = VMSession(
        id=uuid.uuid4(),
        user_id=user.id,
        operating_system_id=os_row.id,
        state=VMState.queued,
        ram_mb=os_row.default_ram_mb,
        vcpus=os_row.default_vcpus,
        network_policy=settings.lab_internet_access_default,
        max_extensions=policy.max_extensions,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    # Actual provisioning (overlay creation + libvirt define/start) is
    # dispatched to the vm-worker queue rather than done inline here, so the
    # API responds immediately and launches queue fairly under load. See
    # app/workers/vm_worker.py:provision_vm for the continuation of this flow.
    return session


async def provision_vm(
    db: AsyncSession,
    *,
    session: VMSession,
    os_row: OperatingSystem,
    libvirt: BaseLibvirtClient,
) -> VMSession:
    """Called by the worker: creates the overlay, starts the domain, records state."""
    session.state = VMState.provisioning
    await db.commit()

    policy = await get_active_policy(db)

    overlay_path = await overlay_manager.create_overlay(
        base_image_path=os_row.base_image_path,
        session_id=str(session.id),
    )

    domain_name = f"knpodly-{session.id}"
    vnc_port = await overlay_manager.allocate_vnc_port()
    domain_xml = render_domain_xml(
        name=domain_name,
        ram_mb=session.ram_mb,
        vcpus=session.vcpus,
        overlay_disk_path=overlay_path,
        vnc_port=vnc_port,
        network_bridge=settings.vm_network_bridge,
        vnc_listen_address=settings.vm_vnc_host,
    )

    try:
        await libvirt.define_and_start(domain_xml, domain_name)
    except Exception:
        session.state = VMState.failed
        await db.commit()
        await overlay_manager.destroy_overlay(overlay_path)
        raise

    now = datetime.now(timezone.utc)
    session.libvirt_domain_name = domain_name
    session.overlay_disk_path = overlay_path
    session.vnc_port = vnc_port
    session.websocket_token = uuid.uuid4().hex
    session.state = VMState.running
    session.started_at = now
    session.expires_at = now + timedelta(minutes=policy.max_session_minutes)
    session.last_activity_at = now
    await db.commit()
    await db.refresh(session)
    return session


async def stop_vm(
    db: AsyncSession, *, session: VMSession, libvirt: BaseLibvirtClient, reason: str, force: bool = False
) -> VMSession:
    session.state = VMState.stopping
    await db.commit()

    if session.libvirt_domain_name:
        if force:
            await libvirt.force_destroy(session.libvirt_domain_name)
        else:
            await libvirt.graceful_shutdown(session.libvirt_domain_name)
        await libvirt.undefine(session.libvirt_domain_name)

    if session.overlay_disk_path:
        await overlay_manager.destroy_overlay(session.overlay_disk_path)
    if session.vnc_port is not None:
        await overlay_manager.release_vnc_port(session.vnc_port)

    # `state` (the machine-readable VMState enum) and `stop_reason` (why it
    # stopped) are deliberately separate columns: the state machine only
    # needs to know the session is no longer running, while stop_reason
    # drives what the frontend/audit log tells the user ("expired",
    # "you stopped it", "a lecturer force-stopped it", "idle timeout").
    session.state = VMState.expired if reason == "expired" else VMState.stopped
    session.stopped_at = datetime.now(timezone.utc)
    session.stop_reason = reason
    await db.commit()
    await db.refresh(session)
    return session


async def extend_session(db: AsyncSession, *, session: VMSession) -> VMSession:
    if session.extension_count >= session.max_extensions:
        raise VMLimitExceeded("No extensions remaining for this session.")
    policy = await get_active_policy(db)
    session.expires_at = (session.expires_at or datetime.now(timezone.utc)) + timedelta(
        minutes=policy.max_extension_minutes
    )
    session.extension_count += 1
    await db.commit()
    await db.refresh(session)
    return session


async def record_activity(db: AsyncSession, *, session: VMSession) -> None:
    """Called by the WS heartbeat endpoint on keyboard/mouse/focus/console activity."""
    session.last_activity_at = datetime.now(timezone.utc)
    session.idle_warning_sent_at = None
    await db.commit()
