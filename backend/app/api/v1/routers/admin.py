"""
Admin/lecturer dashboard endpoints: host stats, maintenance mode, audit log
viewing, VM limit policy configuration.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_libvirt, require_lecturer
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.models.maintenance_window import MaintenanceWindow
from app.models.user import User
from app.models.vm_limit_policy import VMLimitPolicy
from app.models.vm_session import VMSession, VMState
from app.schemas.admin import MaintenanceStatusOut, VMLimitPolicyOut, VMLimitPolicyUpdate
from app.services import audit
from app.services.libvirt_client import BaseLibvirtClient
from app.services.policy import get_active_policy
from app.services.redis_bus import publish_event

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/host-stats")
async def host_stats(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_lecturer),
    libvirt: BaseLibvirtClient = Depends(get_libvirt),
):
    stats = await libvirt.host_stats()
    running_count = (
        await db.execute(select(VMSession).where(VMSession.state == VMState.running))
    ).scalars().all()
    queued_count = (
        await db.execute(select(VMSession).where(VMSession.state == VMState.queued))
    ).scalars().all()
    return {
        "host": stats,
        "running_vms": len(running_count),
        "queued_vms": len(queued_count),
    }


@router.get("/maintenance", response_model=MaintenanceStatusOut)
async def get_maintenance_status(db: AsyncSession = Depends(get_db), _: User = Depends(require_lecturer)):
    active = (
        await db.execute(
            select(MaintenanceWindow)
            .where(MaintenanceWindow.is_active.is_(True))
            .order_by(desc(MaintenanceWindow.started_at))
        )
    ).scalars().first()
    if active is None:
        return MaintenanceStatusOut(is_active=False)
    return MaintenanceStatusOut(is_active=True, message=active.message, started_at=active.started_at)


@router.post("/maintenance/enable")
async def enable_maintenance(message: str, db: AsyncSession = Depends(get_db), user: User = Depends(require_lecturer)):
    # Close out any stale active window first so there's always at most one.
    stale = (
        await db.execute(select(MaintenanceWindow).where(MaintenanceWindow.is_active.is_(True)))
    ).scalars().all()
    for w in stale:
        w.is_active = False
        w.ended_at = datetime.now(timezone.utc)

    db.add(MaintenanceWindow(enabled_by=user.id, message=message, is_active=True))
    await db.commit()

    await audit.record(
        db, actor_id=user.id, actor_role=user.role.value, action="maintenance.enabled",
        metadata={"message": message},
    )
    await publish_event("maintenance.enabled", {"message": message})
    return {"detail": "Maintenance mode enabled"}


@router.post("/maintenance/disable")
async def disable_maintenance(db: AsyncSession = Depends(get_db), user: User = Depends(require_lecturer)):
    active = (
        await db.execute(select(MaintenanceWindow).where(MaintenanceWindow.is_active.is_(True)))
    ).scalars().all()
    for w in active:
        w.is_active = False
        w.ended_at = datetime.now(timezone.utc)
    await db.commit()

    await audit.record(db, actor_id=user.id, actor_role=user.role.value, action="maintenance.disabled")
    await publish_event("maintenance.disabled", {})
    return {"detail": "Maintenance mode disabled"}


@router.get("/vm-limit-policy", response_model=VMLimitPolicyOut)
async def get_vm_limit_policy(db: AsyncSession = Depends(get_db), _: User = Depends(require_lecturer)):
    return await get_active_policy(db)


@router.patch("/vm-limit-policy", response_model=VMLimitPolicyOut)
async def update_vm_limit_policy(
    payload: VMLimitPolicyUpdate, db: AsyncSession = Depends(get_db), user: User = Depends(require_lecturer)
):
    policy = (
        await db.execute(select(VMLimitPolicy).where(VMLimitPolicy.is_active.is_(True)))
    ).scalars().first()
    if policy is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active policy row found")

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(policy, field, value)
    policy.updated_by = user.id
    await db.commit()
    await db.refresh(policy)

    await audit.record(
        db, actor_id=user.id, actor_role=user.role.value, action="vm_limit_policy.updated",
        target_type="vm_limit_policy", target_id=str(policy.id), metadata=updates,
    )
    return policy


@router.get("/audit-logs")
async def get_audit_logs(
    limit: int = 100, db: AsyncSession = Depends(get_db), _: User = Depends(require_lecturer)
):
    logs = (
        await db.execute(select(AuditLog).order_by(desc(AuditLog.created_at)).limit(limit))
    ).scalars().all()
    return logs
