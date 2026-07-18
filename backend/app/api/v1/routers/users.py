"""
User management endpoints — lecturer/admin can create lecturers/students,
reset passwords, disable accounts, list students. Students cannot access
any endpoint in this router except (implicitly) via /auth/change-password.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_lecturer
from app.core.security import hash_password
from app.db.session import get_db
from app.models.user import User, UserRole, UserStatus
from app.schemas.user import UserCreate, UserOut
from app.services import audit

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserOut])
async def list_users(
    role: UserRole | None = None,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_lecturer),
):
    query = select(User)
    if role:
        query = query.where(User.role == role)
    return (await db.execute(query)).scalars().all()


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate, db: AsyncSession = Depends(get_db), actor: User = Depends(require_lecturer)
):
    if payload.role == UserRole.admin and actor.role != UserRole.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins may create admins")

    existing = (await db.execute(select(User).where(User.username == payload.username))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")

    user = User(
        username=payload.username,
        full_name=payload.full_name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role,
        created_by=actor.id,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    await audit.record(
        db, actor_id=actor.id, actor_role=actor.role.value, action="user.created",
        target_type="user", target_id=str(user.id), metadata={"role": user.role.value},
    )
    return user


@router.post("/{user_id}/reset-password")
async def reset_password(
    user_id: uuid.UUID,
    new_password: str,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_lecturer),
):
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.password_hash = hash_password(new_password)
    await db.commit()
    await audit.record(
        db, actor_id=actor.id, actor_role=actor.role.value, action="user.password_reset",
        target_type="user", target_id=str(user.id),
    )
    return {"detail": "Password reset"}


@router.post("/{user_id}/disable")
async def disable_user(
    user_id: uuid.UUID, db: AsyncSession = Depends(get_db), actor: User = Depends(require_lecturer)
):
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.status = UserStatus.disabled
    await db.commit()
    await audit.record(
        db, actor_id=actor.id, actor_role=actor.role.value, action="user.disabled",
        target_type="user", target_id=str(user.id),
    )
    return {"detail": "User disabled"}


@router.post("/{user_id}/enable")
async def enable_user(
    user_id: uuid.UUID, db: AsyncSession = Depends(get_db), actor: User = Depends(require_lecturer)
):
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.status = UserStatus.active
    await db.commit()
    await audit.record(
        db, actor_id=actor.id, actor_role=actor.role.value, action="user.enabled",
        target_type="user", target_id=str(user.id),
    )
    return {"detail": "User enabled"}
