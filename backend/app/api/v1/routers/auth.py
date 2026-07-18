from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.db.session import get_db
from app.models.user import User, UserStatus
from app.schemas.auth import LoginRequest, PasswordChangeRequest, TokenResponse
from app.schemas.user import UserOut
from app.services import audit
from app.services.rate_limit import check_login_rate_limit, reset_login_rate_limit

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me", response_model=UserOut)
async def get_me(user: User = Depends(get_current_user)):
    """Returns the authenticated user's own profile. The frontend uses this
    on load instead of decoding the JWT client-side, since the token only
    carries `sub`/`role` — not username, full name, or account status."""
    return user


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    client_ip = request.client.host if request.client else "unknown"
    await check_login_rate_limit(ip_address=client_ip, username=payload.username)

    user = (
        await db.execute(select(User).where(User.username == payload.username))
    ).scalar_one_or_none()

    if user is None or not verify_password(payload.password, user.password_hash):
        await audit.record(
            db, actor_id=None, actor_role=None, action="auth.login_failed",
            metadata={"username": payload.username}, ip_address=client_ip,
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if user.status != UserStatus.active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")

    await reset_login_rate_limit(ip_address=client_ip, username=payload.username)
    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()
    await audit.record(
        db, actor_id=user.id, actor_role=user.role.value, action="auth.login_success", ip_address=client_ip,
    )

    return TokenResponse(
        access_token=create_access_token(str(user.id), user.role.value),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.post("/change-password")
async def change_password(
    payload: PasswordChangeRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password incorrect")
    user.password_hash = hash_password(payload.new_password)
    await db.commit()
    await audit.record(db, actor_id=user.id, actor_role=user.role.value, action="auth.password_changed")
    return {"detail": "Password updated"}
