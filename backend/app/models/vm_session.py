import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class VMState(str, enum.Enum):
    queued = "queued"
    provisioning = "provisioning"
    running = "running"
    stopping = "stopping"
    stopped = "stopped"
    expired = "expired"
    failed = "failed"
    destroyed = "destroyed"


class VMSession(Base):
    __tablename__ = "vm_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    operating_system_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("operating_systems.id"), nullable=False)
    libvirt_domain_name: Mapped[str | None] = mapped_column(String(255), unique=True)
    overlay_disk_path: Mapped[str | None] = mapped_column(String(500))
    state: Mapped[VMState] = mapped_column(Enum(VMState, name="vm_state"), default=VMState.queued)
    vnc_port: Mapped[int | None] = mapped_column(Integer)
    websocket_token: Mapped[str | None] = mapped_column(String(255))
    ram_mb: Mapped[int] = mapped_column(Integer, nullable=False)
    vcpus: Mapped[int] = mapped_column(Integer, nullable=False)
    network_policy: Mapped[str] = mapped_column(String(20), default="restricted")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    extension_count: Mapped[int] = mapped_column(Integer, default=0)
    max_extensions: Mapped[int] = mapped_column(Integer, default=1)
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    idle_warning_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    stopped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    stop_reason: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="vm_sessions")
