"""
VM lifecycle endpoints — the core of the student experience: launch,
reconnect, stop, extend. Force-stop is lecturer/admin only.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user, get_libvirt, require_lecturer
from app.core.arq_pool import get_arq_pool
from app.core.config import get_settings
from app.db.session import get_db
from app.models.user import User
from app.models.vm_session import VMSession, VMState
from app.schemas.vm_session import VMLaunchRequest, VMSessionOut
from app.services import audit, vm_lifecycle
from app.services.libvirt_client import BaseLibvirtClient

router = APIRouter(prefix="/vms", tags=["vms"])
settings = get_settings()


def _with_console_url(session: VMSession) -> VMSessionOut:
    out = VMSessionOut.model_validate(session)
    if session.state == VMState.running and session.websocket_token:
        out.console_url = f"{settings.novnc_public_base_url}/{session.websocket_token}"
    return out


@router.post("", response_model=VMSessionOut, status_code=status.HTTP_202_ACCEPTED)
async def launch_vm(
    payload: VMLaunchRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    libvirt: BaseLibvirtClient = Depends(get_libvirt),
):
    try:
        session = await vm_lifecycle.launch_vm(db, user=user, os_slug=payload.os_slug, libvirt=libvirt)
    except vm_lifecycle.VMLimitExceeded as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except vm_lifecycle.OSUnavailable as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except vm_lifecycle.MaintenanceActive as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))

    # Hand off actual provisioning (overlay creation + libvirt define/start)
    # to the vm-worker queue so this request returns immediately.
    pool = get_arq_pool()
    await pool.enqueue_job("provision_vm", str(session.id))

    await audit.record(
        db, actor_id=user.id, actor_role=user.role.value, action="vm.launch_requested",
        target_type="vm_session", target_id=str(session.id), metadata={"os_slug": payload.os_slug},
    )
    return _with_console_url(session)


@router.get("/mine", response_model=VMSessionOut | None)
async def get_my_active_vm(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    session = (
        await db.execute(
            select(VMSession).where(
                VMSession.user_id == user.id,
                VMSession.state.in_(
                    [VMState.queued, VMState.provisioning, VMState.running, VMState.stopping]
                ),
            )
        )
    ).scalar_one_or_none()
    return _with_console_url(session) if session else None


@router.get("", response_model=list[VMSessionOut])
async def list_all_vms(db: AsyncSession = Depends(get_db), _: User = Depends(require_lecturer)):
    """Lecturer/admin view of all running/queued VMs across all students."""
    sessions = (
        await db.execute(
            select(VMSession).where(
                VMSession.state.in_(
                    [VMState.queued, VMState.provisioning, VMState.running, VMState.stopping]
                )
            )
        )
    ).scalars().all()
    return [_with_console_url(s) for s in sessions]


async def _get_owned_or_403(db: AsyncSession, user: User, session_id: uuid.UUID) -> VMSession:
    session = (await db.execute(select(VMSession).where(VMSession.id == session_id))).scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if session.user_id != user.id and user.role.value == "student":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your VM")
    return session


@router.post("/{session_id}/stop", response_model=VMSessionOut)
async def stop_vm(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    libvirt: BaseLibvirtClient = Depends(get_libvirt),
):
    session = await _get_owned_or_403(db, user, session_id)
    session = await vm_lifecycle.stop_vm(db, session=session, libvirt=libvirt, reason="user_stop")
    await audit.record(
        db, actor_id=user.id, actor_role=user.role.value, action="vm.stopped",
        target_type="vm_session", target_id=str(session.id),
    )
    return _with_console_url(session)


@router.post("/{session_id}/force-stop", response_model=VMSessionOut)
async def force_stop_vm(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_lecturer),
    libvirt: BaseLibvirtClient = Depends(get_libvirt),
):
    session = (await db.execute(select(VMSession).where(VMSession.id == session_id))).scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    session = await vm_lifecycle.stop_vm(db, session=session, libvirt=libvirt, reason="force_stop", force=True)
    await audit.record(
        db, actor_id=user.id, actor_role=user.role.value, action="vm.force_stopped",
        target_type="vm_session", target_id=str(session.id),
    )
    return _with_console_url(session)


@router.post("/{session_id}/extend", response_model=VMSessionOut)
async def extend_vm(
    session_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    session = await _get_owned_or_403(db, user, session_id)
    try:
        session = await vm_lifecycle.extend_session(db, session=session)
    except vm_lifecycle.VMLimitExceeded as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    await audit.record(
        db, actor_id=user.id, actor_role=user.role.value, action="vm.extended",
        target_type="vm_session", target_id=str(session.id),
    )
    return _with_console_url(session)


@router.post("/{session_id}/activity", status_code=status.HTTP_204_NO_CONTENT)
async def report_activity(
    session_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    """Called by the frontend's activity heartbeat (keyboard/mouse/focus/console
    events) to reset the idle timer. See docs/architecture.md#idle-detection."""
    session = await _get_owned_or_403(db, user, session_id)
    await vm_lifecycle.record_activity(db, session=session)
