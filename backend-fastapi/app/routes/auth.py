"""
routes/auth.py — Authentication: signup, login, OTP, me, logout
Rewritten for MySQL/SQLAlchemy
"""

import os
import random
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.orm_models import User
from app.auth.jwt import hash_password, verify_password, create_access_token, create_refresh_token
from app.auth.deps import get_current_user
from app.models.user import SignupRequest, LoginRequest, OTPVerifyRequest, UserResponse, TokenResponse

router = APIRouter(prefix="/api/auth", tags=["Auth"])

EMAIL_ENABLED = bool(os.getenv("MAIL_USERNAME"))


def _user_resp(user: User) -> UserResponse:
    return UserResponse(
        id=str(user.id),
        username=user.username,
        email=user.email,
        role=user.role,
        is_admin=(user.role == "admin"),
        created_at=user.created_at.isoformat() if isinstance(user.created_at, datetime) else str(user.created_at or "")
    )


@router.post("/signup")
async def signup(data: SignupRequest, db: AsyncSession = Depends(get_db)):
    if data.password != data.confirm_password:
        raise HTTPException(400, "Passwords do not match")

    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none():
        raise HTTPException(409, "Email already registered")

    # First user becomes admin
    count_result = await db.execute(select(User))
    is_first = len(count_result.all()) == 0
    role = "admin" if is_first else "cadet"

    user = User(
        username=data.username,
        email=data.email,
        password_hash=hash_password(data.password),
        role=role,
        created_at=datetime.utcnow()
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    access = create_access_token({"sub": str(user.id), "role": role})
    refresh = create_refresh_token({"sub": str(user.id)})
    return TokenResponse(access_token=access, refresh_token=refresh, user=_user_resp(user))


@router.post("/login")
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    # Try by email first, then by username (for cadets using roll number)
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    if not user:
        result2 = await db.execute(select(User).where(User.username == data.email))
        user = result2.scalar_one_or_none()

    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")

    otp = str(random.randint(100000, 999999))
    user.otp_code = hash_password(otp)
    user.otp_expiry = datetime.utcnow() + timedelta(minutes=5)
    await db.commit()

    if EMAIL_ENABLED:
        try:
            from app.utils.email import send_otp_email
            await send_otp_email(user.email, user.username, otp)
        except Exception as e:
            print(f"Email error: {e}")
    else:
        print(f"\n🔑 OTP for {user.email}: {otp}\n")

    return {
        "success": True,
        "otp_required": True,
        "email": user.email,
        "message": "OTP sent to email (check console in dev mode)"
    }


@router.post("/verify-otp", response_model=TokenResponse)
async def verify_otp(data: OTPVerifyRequest, db: AsyncSession = Depends(get_db)):
    # Look up by email or username
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    if not user:
        result2 = await db.execute(select(User).where(User.username == data.email))
        user = result2.scalar_one_or_none()

    if not user or not user.otp_code:
        raise HTTPException(400, "OTP flow not initiated")
    if not user.otp_expiry or datetime.utcnow() > user.otp_expiry:
        raise HTTPException(400, "OTP expired. Please login again.")
    if not verify_password(data.otp, user.otp_code):
        raise HTTPException(401, "Invalid OTP code")

    user.otp_code = None
    user.otp_expiry = None
    await db.commit()

    access = create_access_token({"sub": str(user.id), "role": user.role})
    refresh = create_refresh_token({"sub": str(user.id)})
    return TokenResponse(access_token=access, refresh_token=refresh, user=_user_resp(user))


@router.get("/me")
async def me(user: User = Depends(get_current_user)):
    return {"authenticated": True, "user": _user_resp(user)}


@router.post("/logout")
async def logout(_: User = Depends(get_current_user)):
    return {"success": True, "message": "Logged out successfully"}
