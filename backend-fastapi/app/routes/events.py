"""
routes/events.py — NCC Event Calendar endpoints
MySQL/SQLAlchemy
"""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Form, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.database import get_db
from app.models.orm_models import Event, User
from app.auth.deps import require_admin

router = APIRouter(prefix="/api/events", tags=["Events"])


def _event(e: Event) -> dict:
    return {
        "id": e.id,
        "title": e.title,
        "description": e.description or "",
        "event_type": e.event_type,
        "start_date": e.start_date.isoformat() if isinstance(e.start_date, datetime) else str(e.start_date or ""),
        "end_date": e.end_date.isoformat() if isinstance(e.end_date, datetime) else str(e.end_date or ""),
        "location": e.location or "",
        "is_mandatory": e.is_mandatory,
        "created_at": e.created_at.isoformat() if isinstance(e.created_at, datetime) else ""
    }


@router.get("/")
async def get_events(
    upcoming_only: bool = Query(False),
    db: AsyncSession = Depends(get_db)
):
    q = select(Event)
    if upcoming_only:
        q = q.where(Event.start_date >= datetime.utcnow())
    q = q.order_by(Event.start_date)
    result = await db.execute(q)
    return {"success": True, "events": [_event(e) for e in result.scalars().all()]}


@router.post("/")
async def create_event(
    title: str = Form(...),
    description: str = Form(""),
    event_type: str = Form(...),   # Camp | Parade | Social | Exam | Other
    start_date: str = Form(...),   # ISO format: 2025-04-15T09:00:00
    end_date: str = Form(...),
    location: str = Form(""),
    is_mandatory: bool = Form(False),
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    try:
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)
    except ValueError:
        raise HTTPException(400, "Invalid date format. Use ISO 8601: YYYY-MM-DDTHH:MM:SS")

    event = Event(
        title=title, description=description, event_type=event_type,
        start_date=start, end_date=end, location=location,
        is_mandatory=is_mandatory, created_at=datetime.utcnow()
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return {"success": True, "event": _event(event)}


@router.delete("/{eid}")
async def delete_event(
    eid: int,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Event).where(Event.id == eid))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(404, "Event not found")
    await db.delete(event)
    await db.commit()
    return {"success": True}
