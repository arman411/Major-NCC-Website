"""
models/student.py — Pydantic schemas for Student/Cadet enrollment
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class EnrollmentRequest(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    dob: str  # YYYY-MM-DD
    gender: str
    phone: str = Field(..., min_length=10)
    email: EmailStr
    address: Optional[str] = ""
    roll_no: str = Field(..., min_length=1)
    branch: str
    year: str
    ncc_wing: str  # Army / Naval / Air
    prev_experience: Optional[str] = "None"
    motivation: Optional[str] = ""

class StatusUpdateRequest(BaseModel):
    status: str  # pending / approved / rejected
    cadet_no: Optional[str] = None
    remarks: Optional[str] = None

class StudentResponse(BaseModel):
    id: str
    first_name: str
    last_name: str
    full_name: str
    dob: str
    gender: str
    phone: str
    email: str
    address: Optional[str]
    roll_no: str
    branch: str
    year: str
    ncc_wing: str
    prev_experience: Optional[str]
    motivation: Optional[str]
    photo_url: Optional[str]
    status: str
    cadet_no: Optional[str]
    remarks: Optional[str]
    enrolled_at: Optional[str]
