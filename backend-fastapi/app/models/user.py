"""
models/user.py — Pydantic request/response models for Auth
"""

from typing import Optional
from pydantic import BaseModel, EmailStr


class SignupRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    confirm_password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class OTPVerifyRequest(BaseModel):
    email: EmailStr
    otp: str


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    role: str
    is_admin: bool
    created_at: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse
