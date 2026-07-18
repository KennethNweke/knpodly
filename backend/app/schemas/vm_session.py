import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.vm_session import VMState


class VMLaunchRequest(BaseModel):
    os_slug: str


class VMSessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    operating_system_id: uuid.UUID
    state: VMState
    ram_mb: int
    vcpus: int
    network_policy: str
    started_at: datetime | None
    expires_at: datetime | None
    extension_count: int
    max_extensions: int
    console_url: str | None = None
