from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MaintenanceStatusOut(BaseModel):
    is_active: bool
    message: str | None = None
    started_at: datetime | None = None


class VMLimitPolicyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    max_session_minutes: int
    max_extension_minutes: int
    max_extensions: int
    idle_warning_minutes: int
    idle_timeout_minutes: int
    max_concurrent_vms_total: int
    updated_at: datetime


class VMLimitPolicyUpdate(BaseModel):
    max_session_minutes: int | None = None
    max_extension_minutes: int | None = None
    max_extensions: int | None = None
    idle_warning_minutes: int | None = None
    idle_timeout_minutes: int | None = None
    max_concurrent_vms_total: int | None = None
