"""
models/orm_models.py — SQLAlchemy ORM Table Definitions
NCC Unit – Govt. Polytechnic Hamirpur (HP)
All tables use Integer auto-increment PKs (MySQL compatible).
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Boolean,
    DateTime, ForeignKey, Index
)
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    username      = Column(String(100), nullable=False)
    email         = Column(String(200), unique=True, nullable=False)
    password_hash = Column(String(300), nullable=False)
    role          = Column(String(20), default="cadet")   # cadet | admin
    otp_code      = Column(String(300), nullable=True)
    otp_expiry    = Column(DateTime, nullable=True)
    created_at    = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_users_email", "email"),
    )


class Student(Base):
    __tablename__ = "students"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    first_name     = Column(String(100), nullable=False)
    last_name      = Column(String(100), nullable=False)
    dob            = Column(String(20))
    gender         = Column(String(20))
    phone          = Column(String(20))
    email          = Column(String(200))
    address        = Column(Text)
    roll_no        = Column(String(50), unique=True)
    branch         = Column(String(100))
    year           = Column(String(10))
    institution    = Column(String(200), default="Govt. Polytechnic Hamirpur (HP)")
    ncc_wing       = Column(String(50))
    prev_experience = Column(Text)
    motivation     = Column(Text)
    photo_path     = Column(String(300), nullable=True)
    status         = Column(String(20), default="pending")  # pending|approved|rejected
    cadet_no       = Column(String(50), nullable=True)
    remarks        = Column(Text, nullable=True)
    enrolled_at    = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_students_roll_no", "roll_no"),
        Index("ix_students_status", "status"),
    )


class Notice(Base):
    __tablename__ = "notices"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    title       = Column(String(300), nullable=False)
    category    = Column(String(50))   # Camp | Exam | Urgent | General | Social
    description = Column(Text)
    issued_by   = Column(String(100), default="ANO Office")
    deadline    = Column(String(50), nullable=True)
    file_path   = Column(String(300), nullable=True)
    is_new      = Column(Boolean, default=True)
    created_at  = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_notices_category", "category"),
        Index("ix_notices_created_at", "created_at"),
    )


class GalleryItem(Base):
    __tablename__ = "gallery_items"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    title       = Column(String(200), nullable=False)
    category    = Column(String(50))   # Camps | Social | Campus | Parade
    description = Column(Text)
    image_path  = Column(String(300), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_gallery_category", "category"),
    )


class Camp(Base):
    __tablename__ = "camps"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    name             = Column(String(200), nullable=False)
    location         = Column(String(200))
    camp_type        = Column(String(50))
    start_date       = Column(String(50))
    end_date         = Column(String(50))
    description      = Column(Text)
    is_upcoming      = Column(Boolean, default=True)
    capacity         = Column(Integer, default=50)
    registered_count = Column(Integer, default=0)
    created_at       = Column(DateTime, default=datetime.utcnow)


class Achievement(Base):
    __tablename__ = "achievements"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    cadet_name  = Column(String(200), nullable=False)
    title       = Column(String(300), nullable=False)
    description = Column(Text)
    year        = Column(Integer)
    level       = Column(String(50))   # State | National | International
    image_path  = Column(String(300), nullable=True)
    created_at  = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_achievements_year", "year"),
        Index("ix_achievements_level", "level"),
    )


class ContactMessage(Base):
    __tablename__ = "contact_messages"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    name       = Column(String(200), nullable=False)
    email      = Column(String(200), nullable=False)
    phone      = Column(String(20))
    subject    = Column(String(300))
    message    = Column(Text)
    is_read    = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Analytics(Base):
    __tablename__ = "analytics"

    id        = Column(Integer, primary_key=True, autoincrement=True)
    page      = Column(String(200))
    timestamp = Column(DateTime, default=datetime.utcnow)


class CadetPoints(Base):
    __tablename__ = "cadet_points"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    student_id  = Column(Integer, ForeignKey("students.id"), nullable=True)
    cadet_name  = Column(String(200), nullable=False)
    branch      = Column(String(100))
    points      = Column(Integer, default=0)
    rank_pos    = Column(Integer, nullable=True)
    updated_at  = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_cadet_points_points", "points"),
    )


class Event(Base):
    __tablename__ = "events"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    title        = Column(String(200), nullable=False)
    description  = Column(Text)
    event_type   = Column(String(50))  # Camp | Parade | Social | Exam | Other
    start_date   = Column(DateTime)
    end_date     = Column(DateTime)
    location     = Column(String(200))
    is_mandatory = Column(Boolean, default=False)
    created_at   = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_events_start_date", "start_date"),
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    action     = Column(String(300))
    user_id    = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
