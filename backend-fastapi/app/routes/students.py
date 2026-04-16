"""
routes/students.py — Cadet enrollment & management
Rewritten for MySQL/SQLAlchemy
"""

import os, re
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models.orm_models import Student, User
from app.auth.deps import get_current_user, require_admin
from app.utils.upload import save_upload_file

router = APIRouter(prefix="/api/students", tags=["Students"])


def _stu(s: Student) -> dict:
    return {
        "id": s.id,
        "first_name": s.first_name,
        "last_name": s.last_name,
        "full_name": f"{s.first_name} {s.last_name}",
        "dob": s.dob,
        "gender": s.gender,
        "phone": s.phone,
        "email": s.email,
        "address": s.address,
        "roll_no": s.roll_no,
        "branch": s.branch,
        "year": s.year,
        "ncc_wing": s.ncc_wing,
        "prev_experience": s.prev_experience,
        "motivation": s.motivation,
        "photo_url": f"/uploads/{s.photo_path}" if s.photo_path else None,
        "status": s.status,
        "cadet_no": s.cadet_no,
        "remarks": s.remarks,
        "enrolled_at": s.enrolled_at.isoformat() if isinstance(s.enrolled_at, datetime) else str(s.enrolled_at or "")
    }


@router.post("/enroll")
async def enroll(
    first_name: str = Form(...),
    last_name: str = Form(...),
    dob: str = Form(...),
    gender: str = Form(...),
    phone: str = Form(...),
    email: str = Form(...),
    roll_no: str = Form(...),
    branch: str = Form(...),
    year: str = Form(...),
    ncc_wing: str = Form(...),
    address: str = Form(""),
    prev_experience: str = Form("None"),
    motivation: str = Form(""),
    photo: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db)
):
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        raise HTTPException(400, "Invalid email format")

    existing = await db.execute(select(Student).where(Student.roll_no == roll_no.strip()))
    if existing.scalar_one_or_none():
        raise HTTPException(409, "A student with this roll number is already enrolled")

    photo_filename = None
    if photo and photo.filename:
        photo_filename = await save_upload_file(photo)

    student = Student(
        first_name=first_name.strip(),
        last_name=last_name.strip(),
        dob=dob.strip(),
        gender=gender.strip(),
        phone=phone.strip(),
        email=email.strip(),
        address=address.strip(),
        roll_no=roll_no.strip(),
        branch=branch.strip(),
        year=year.strip(),
        ncc_wing=ncc_wing.strip(),
        prev_experience=prev_experience.strip(),
        motivation=motivation.strip(),
        photo_path=photo_filename,
        status="pending",
        enrolled_at=datetime.utcnow()
    )
    db.add(student)
    await db.commit()
    await db.refresh(student)
    return {
        "success": True,
        "message": "Enrollment submitted! ANO office will contact you within 3-5 days.",
        "student_id": student.id,
        "reference": f"GPH-NCC-{student.id:05d}"
    }


@router.get("/")
async def get_students(
    status: Optional[str] = Query(None),
    branch: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(Student)
    if status:
        query = query.where(Student.status == status)
    if branch:
        query = query.where(Student.branch == branch)
    if search:
        like = f"%{search}%"
        query = query.where(or_(
            Student.first_name.ilike(like),
            Student.last_name.ilike(like),
            Student.roll_no.ilike(like),
            Student.email.ilike(like)
        ))

    count_q = select(func.count()).select_from(query.subquery())
    total_res = await db.execute(count_q)
    total = total_res.scalar()

    query = query.order_by(Student.enrolled_at.desc()).offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    students = result.scalars().all()
    return {
        "success": True,
        "students": [_stu(s) for s in students],
        "pagination": {"page": page, "per_page": per_page, "total": total, "pages": -(-total // per_page)}
    }


@router.get("/{student_id}")
async def get_student(
    student_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Student).where(Student.id == student_id))
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(404, "Student not found")
    return {"success": True, "student": _stu(student)}


@router.patch("/{student_id}/status")
async def update_status(
    student_id: int,
    status: str = Form(...),
    cadet_no: Optional[str] = Form(None),
    remarks: Optional[str] = Form(None),
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    if status not in ("pending", "approved", "rejected"):
        raise HTTPException(400, "Invalid status")
    result = await db.execute(select(Student).where(Student.id == student_id))
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(404, "Student not found")
    student.status = status
    if cadet_no:
        student.cadet_no = cadet_no
    if remarks:
        student.remarks = remarks
    await db.commit()
    await db.refresh(student)
    return {"success": True, "student": _stu(student)}


@router.delete("/{student_id}")
async def delete_student(
    student_id: int,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Student).where(Student.id == student_id))
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(404, "Student not found")
    await db.delete(student)
    await db.commit()
    return {"success": True, "message": "Student deleted"}
