import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.user import UserRole, UserStatus


class UserCreate(BaseModel):
    username: str
    full_name: str
    email: str | None = None
    password: str
    role: UserRole = UserRole.student


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    full_name: str
    email: str | None
    role: UserRole
    status: UserStatus
    created_at: datetime
    last_login_at: datetime | None
