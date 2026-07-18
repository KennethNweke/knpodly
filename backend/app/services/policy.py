"""
Central place to read the currently active VM limit policy. Lecturers edit
these via the admin UI (POST /api/v1/admin/vm-limit-policy); everything
that previously read hardcoded values from app.core.config (session
duration, extension rules, idle timeouts, concurrency cap) should go
through here instead, so a policy change takes effect immediately for the
next launch/sweep without a restart.

`app.core.config.Settings` values remain as the seed/fallback defaults used
to create the initial `default` policy row (see
infra/postgres/init/001_schema.sql) and as a safety net if no active row
exists for some reason.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.vm_limit_policy import VMLimitPolicy

settings = get_settings()


async def get_active_policy(db: AsyncSession) -> VMLimitPolicy:
    policy = (
        await db.execute(
            select(VMLimitPolicy).where(VMLimitPolicy.is_active.is_(True)).order_by(VMLimitPolicy.updated_at.desc())
        )
    ).scalars().first()

    if policy is not None:
        return policy

    # No policy row exists (fresh install before the schema seed ran, or it
    # was deleted) — fall back to config defaults rather than crashing.
    return VMLimitPolicy(
        name="fallback-defaults",
        max_session_minutes=settings.session_max_duration_minutes,
        max_extension_minutes=settings.session_max_extension_minutes,
        max_extensions=settings.session_max_extensions,
        idle_warning_minutes=settings.idle_warning_minutes,
        idle_timeout_minutes=settings.idle_timeout_minutes,
        max_concurrent_vms_total=settings.vm_max_concurrent_total,
    )
