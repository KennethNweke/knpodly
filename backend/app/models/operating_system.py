import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class OSStatus(str, enum.Enum):
    available = "available"
    coming_soon = "coming_soon"
    disabled = "disabled"
    validating = "validating"


class OperatingSystem(Base):
    """
    Represents one entry in the OS catalogue, mirrored from a directory in
    VMImages/<slug>/ containing base.qcow2, metadata.json, and splash.png.
    Rows here are created/updated automatically by
    app.services.image_discovery.ImageDiscoveryService — do not hand-edit
    in production; edit metadata.json and let the watcher resync instead.
    """
    __tablename__ = "operating_systems"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    family: Mapped[str] = mapped_column(String(100), nullable=False)
    package_manager: Mapped[str | None] = mapped_column(String(50))
    architecture: Mapped[str] = mapped_column(String(20), default="x86_64")
    description: Mapped[str | None] = mapped_column(Text)
    icon_path: Mapped[str | None] = mapped_column(String(500))
    default_ram_mb: Mapped[int] = mapped_column(Integer, default=2048)
    default_vcpus: Mapped[int] = mapped_column(Integer, default=2)
    base_image_path: Mapped[str | None] = mapped_column(String(500))
    estimated_boot_secs: Mapped[int] = mapped_column(Integer, default=30)
    status: Mapped[OSStatus] = mapped_column(Enum(OSStatus, name="os_status"), default=OSStatus.validating)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64))
    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
