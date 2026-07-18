import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class VMLimitPolicy(Base):
    """
    Configurable session/idle/concurrency limits, editable by lecturers via
    the admin UI. Exactly one row should have is_active=True at a time —
    `app.services.policy.get_active_policy` enforces that by construction
    (it always reads the most recently updated active row).
    """
    __tablename__ = "vm_limit_policies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), default="default")
    max_session_minutes: Mapped[int] = mapped_column(Integer, default=120)
    max_extension_minutes: Mapped[int] = mapped_column(Integer, default=60)
    max_extensions: Mapped[int] = mapped_column(Integer, default=1)
    idle_warning_minutes: Mapped[int] = mapped_column(Integer, default=15)
    idle_timeout_minutes: Mapped[int] = mapped_column(Integer, default=20)
    max_concurrent_vms_total: Mapped[int] = mapped_column(Integer, default=200)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
