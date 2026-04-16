"""
models/models.py — Pydantic request models for API routes
NCC Unit – Govt. Polytechnic Hamirpur (HP)
"""

from typing import Optional
from pydantic import BaseModel


class NoticeCreate(BaseModel):
    title: str
    category: str
    description: str
    issued_by: str = "ANO Office"
    deadline: Optional[str] = None


class GalleryCreate(BaseModel):
    title: str
    category: str
    description: str = ""


class CampCreate(BaseModel):
    name: str
    location: str
    camp_type: str
    start_date: str
    end_date: str
    description: str = ""
    is_upcoming: bool = True
    capacity: int = 50


class AchievementCreate(BaseModel):
    cadet_name: str
    title: str
    description: str = ""
    year: int
    level: str


class ContactCreate(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    subject: Optional[str] = None
    message: str
