import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.operating_system import OSStatus


class OperatingSystemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    name: str
    family: str
    package_manager: str | None
    architecture: str
    description: str | None
    icon_path: str | None
    default_ram_mb: int
    default_vcpus: int
    estimated_boot_secs: int
    status: OSStatus
    updated_at: datetime
