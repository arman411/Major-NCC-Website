"""
routes/certificates.py — PDF Certificate Generator using ReportLab
NCC Unit – Govt. Polytechnic Hamirpur (HP)
"""

import os
import io
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.orm_models import Student, User
from app.auth.deps import get_current_user

router = APIRouter(prefix="/api/certificates", tags=["Certificates"])


def _generate_pdf(student: Student) -> bytes:
    """Generate a participation certificate PDF using ReportLab."""
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.units import mm, cm
    from reportlab.pdfgen import canvas
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import Paragraph
    from reportlab.lib.enums import TA_CENTER

    page_width, page_height = landscape(A4)
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=landscape(A4))

    # Background gradient simulation
    c.setFillColor(colors.HexColor("#0d2b5e"))
    c.rect(0, 0, page_width, page_height, fill=1, stroke=0)

    c.setFillColor(colors.HexColor("#1a3a7a"))
    c.rect(0, page_height * 0.6, page_width, page_height * 0.4, fill=1, stroke=0)

    # Decorative border
    c.setStrokeColor(colors.HexColor("#c8a84b"))
    c.setLineWidth(3)
    c.rect(20, 20, page_width - 40, page_height - 40, fill=0, stroke=1)
    c.setLineWidth(1)
    c.rect(30, 30, page_width - 60, page_height - 60, fill=0, stroke=1)

    # Header
    c.setFillColor(colors.HexColor("#c8a84b"))
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(page_width / 2, page_height - 70, "NATIONAL CADET CORPS (NCC)")
    c.setFont("Helvetica", 11)
    c.drawCentredString(page_width / 2, page_height - 90, "Govt. Polytechnic Hamirpur (HP)")

    # Certificate title
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 38)
    c.drawCentredString(page_width / 2, page_height / 2 + 60, "CERTIFICATE")
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(page_width / 2, page_height / 2 + 30, "OF ENROLLMENT")

    # Body text
    c.setFont("Helvetica", 13)
    c.drawCentredString(page_width / 2, page_height / 2 - 10, "This is to certify that")

    c.setFillColor(colors.HexColor("#c8a84b"))
    c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(page_width / 2, page_height / 2 - 40, f"{student.first_name} {student.last_name}")

    c.setFillColor(colors.white)
    c.setFont("Helvetica", 12)
    c.drawCentredString(page_width / 2, page_height / 2 - 70,
                        f"Roll No: {student.roll_no}  |  Branch: {student.branch}  |  NCC Wing: {student.ncc_wing}")
    c.drawCentredString(page_width / 2, page_height / 2 - 90,
                        "has been successfully enrolled in the NCC Unit of")
    c.drawCentredString(page_width / 2, page_height / 2 - 110,
                        "Government Polytechnic Hamirpur, Himachal Pradesh.")

    if student.cadet_no:
        c.setFillColor(colors.HexColor("#c8a84b"))
        c.setFont("Helvetica-Bold", 13)
        c.drawCentredString(page_width / 2, page_height / 2 - 135,
                            f"Cadet No: {student.cadet_no}")
        c.setFillColor(colors.white)

    # Date
    c.setFont("Helvetica", 11)
    date_str = student.enrolled_at.strftime("%d %B %Y") if isinstance(student.enrolled_at, datetime) else "N/A"
    c.drawCentredString(page_width / 2, 90, f"Date of Enrollment: {date_str}")

    # Signature lines
    c.setStrokeColor(colors.HexColor("#c8a84b"))
    c.setLineWidth(1)
    sig_y = 75
    c.line(80, sig_y, 200, sig_y)
    c.line(page_width - 200, sig_y, page_width - 80, sig_y)
    
    c.setFont("Helvetica", 10)
    c.drawCentredString(140, sig_y - 15, "Associate NCC Officer (ANO)")
    c.drawCentredString(page_width - 140, sig_y - 15, "Principal, GPH Hamirpur")

    # Seal placeholder
    c.setStrokeColor(colors.HexColor("#c8a84b"))
    c.setLineWidth(2)
    c.circle(page_width / 2, 65, 30, fill=0, stroke=1)
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(page_width / 2, 70, "OFFICIAL")
    c.drawCentredString(page_width / 2, 58, "SEAL")

    c.save()
    buf.seek(0)
    return buf.read()


@router.get("/generate/{student_id}")
async def generate_certificate(
    student_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Student).where(Student.id == student_id))
    student = result.scalar_one_or_none()

    if not student:
        raise HTTPException(404, "Student not found")

    # Cadets can only generate their own certificate; admins can generate any
    if current_user.role != "admin" and str(student.email) != current_user.email:
        raise HTTPException(403, "You can only download your own certificate")

    if student.status != "approved":
        raise HTTPException(400, "Certificate available only after enrollment is approved")

    pdf_bytes = _generate_pdf(student)
    filename = f"NCC_Certificate_{student.first_name}_{student.last_name}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.get("/mine")
async def my_certificates(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Cadet fetches their own enrollment certificate status."""
    result = await db.execute(select(Student).where(Student.email == current_user.email))
    student = result.scalar_one_or_none()

    if not student:
        return {"success": True, "certificates": [], "message": "No enrollment found for this account"}

    return {
        "success": True,
        "student_id": student.id,
        "status": student.status,
        "can_download": student.status == "approved",
        "certificates": [
            {
                "type": "Enrollment Certificate",
                "available": student.status == "approved",
                "download_url": f"/api/certificates/generate/{student.id}" if student.status == "approved" else None
            }
        ]
    }
