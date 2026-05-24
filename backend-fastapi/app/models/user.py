"""
models/user.py — Pydantic request/response models for Auth
"""

from typing import Optional
from pydantic import BaseModel


class SignupRequest(BaseModel):
    username: str
    email: str          # plain str so roll numbers also work during signup
    password: str
    confirm_password: str


class LoginRequest(BaseModel):
    email: str          # accepts email OR roll number / username
    password: str


class OTPVerifyRequest(BaseModel):
    email: str          # same identifier used during login
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
