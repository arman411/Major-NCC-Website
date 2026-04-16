"""
routes/api.py — Notices, Gallery, Camps, Achievements, Contact, Dashboard, Analytics, Leaderboard, Stats
Rewritten for MySQL/SQLAlchemy with new endpoints
"""

from datetime import datetime
from typing import Optional, List
from fastapi import (
    APIRouter, HTTPException, Depends,
    UploadFile, File, Form, Query, WebSocket, WebSocketDisconnect
)
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, desc

from app.database import get_db
from app.models.orm_models import (
    Notice, GalleryItem, Camp, Achievement,
    ContactMessage, Student, User, Analytics, CadetPoints
)
from app.auth.deps import get_current_user, require_admin
from app.models.models import NoticeCreate, GalleryCreate, CampCreate, AchievementCreate, ContactCreate
from app.utils.upload import save_upload_file

# ── WebSocket connection manager ──────────────────────────────────────────────
class NoticeConnectionManager:
    def __init__(self):
        self.connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.connections.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.connections:
            self.connections.remove(ws)

    async def broadcast(self, message: dict):
        import json
        for conn in self.connections[:]:
            try:
                await conn.send_text(json.dumps(message))
            except Exception:
                self.disconnect(conn)

ws_manager = NoticeConnectionManager()


# ╔══════════════════════════════════════════════════════════╗
# ║  PUBLIC STATS                                           ║
# ╚══════════════════════════════════════════════════════════╝
stats_router = APIRouter(prefix="/api/stats", tags=["Stats"])

@stats_router.get("/public")
async def public_stats(db: AsyncSession = Depends(get_db)):
    """Public endpoint — no auth required. Returns site-wide counts."""
    total_cadets = (await db.execute(select(func.count()).select_from(Student))).scalar()
    approved = (await db.execute(
        select(func.count()).select_from(Student).where(Student.status == "approved")
    )).scalar()
    total_achievements = (await db.execute(select(func.count()).select_from(Achievement))).scalar()
    total_camps = (await db.execute(select(func.count()).select_from(Camp))).scalar()
    return {
        "success": True,
        "stats": {
            "active_cadets": approved or total_cadets,
            "total_cadets": total_cadets,
            "camps_attended": total_camps,
            "awards_won": total_achievements,
            "years_of_service": 25
        }
    }


# ╔══════════════════════════════════════════════════════════╗
# ║  LEADERBOARD                                            ║
# ╚══════════════════════════════════════════════════════════╝
leaderboard_router = APIRouter(prefix="/api/leaderboard", tags=["Leaderboard"])

@leaderboard_router.get("/")
async def get_leaderboard(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(CadetPoints).order_by(desc(CadetPoints.points)).limit(10)
    )
    entries = result.scalars().all()
    return {
        "success": True,
        "leaderboard": [
            {
                "rank": idx + 1,
                "id": e.id,
                "cadet_name": e.cadet_name,
                "branch": e.branch,
                "points": e.points,
                "student_id": e.student_id
            }
            for idx, e in enumerate(entries)
        ]
    }


# ╔══════════════════════════════════════════════════════════╗
# ║  NOTICES                                                ║
# ╚══════════════════════════════════════════════════════════╝
notices_router = APIRouter(prefix="/api/notices", tags=["Notices"])

def _notice(n: Notice) -> dict:
    return {
        "id": n.id,
        "title": n.title,
        "category": n.category,
        "description": n.description,
        "issued_by": n.issued_by,
        "deadline": n.deadline,
        "file_url": f"/uploads/{n.file_path}" if n.file_path else None,
        "is_new": n.is_new,
        "created_at": n.created_at.isoformat() if isinstance(n.created_at, datetime) else str(n.created_at or "")
    }

@notices_router.get("/")
async def get_notices(
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    db: AsyncSession = Depends(get_db)
):
    q = select(Notice)
    if category and category.lower() != "all":
        q = q.where(Notice.category.ilike(f"%{category}%"))
    if search:
        like = f"%{search}%"
        q = q.where(or_(Notice.title.ilike(like), Notice.description.ilike(like)))
    
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar()
    q = q.order_by(desc(Notice.created_at)).offset((page - 1) * 20).limit(20)
    result = await db.execute(q)
    items = result.scalars().all()
    return {"success": True, "notices": [_notice(n) for n in items], "total": total}


# WebSocket for real-time notice alerts
@notices_router.websocket("/ws")
async def notices_ws(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


@notices_router.post("/")
async def create_notice(
    title: str = Form(...),
    category: str = Form(...),
    description: str = Form(...),
    issued_by: str = Form("ANO Office"),
    deadline: str = Form(None),
    file: Optional[UploadFile] = File(None),
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    fp = await save_upload_file(file) if file and file.filename else None
    notice = Notice(
        title=title, category=category, description=description,
        issued_by=issued_by, deadline=deadline, file_path=fp,
        is_new=True, created_at=datetime.utcnow()
    )
    db.add(notice)
    await db.commit()
    await db.refresh(notice)
    # Broadcast to WebSocket clients
    await ws_manager.broadcast({"type": "new_notice", "notice": _notice(notice)})
    return {"success": True, "notice": _notice(notice)}

@notices_router.delete("/{nid}")
async def delete_notice(nid: int, user: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Notice).where(Notice.id == nid))
    n = result.scalar_one_or_none()
    if not n:
        raise HTTPException(404, "Notice not found")
    await db.delete(n)
    await db.commit()
    return {"success": True}


# ╔══════════════════════════════════════════════════════════╗
# ║  GALLERY                                                ║
# ╚══════════════════════════════════════════════════════════╝
gallery_router = APIRouter(prefix="/api/gallery", tags=["Gallery"])

def _gallery(g: GalleryItem) -> dict:
    return {
        "id": g.id, "title": g.title, "category": g.category,
        "description": g.description or "",
        "image_url": f"/uploads/{g.image_path}",
        "uploaded_at": g.uploaded_at.isoformat() if isinstance(g.uploaded_at, datetime) else str(g.uploaded_at or "")
    }

@gallery_router.get("/")
async def get_gallery(
    category: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    db: AsyncSession = Depends(get_db)
):
    q = select(GalleryItem)
    if category and category.lower() != "all":
        q = q.where(GalleryItem.category.ilike(category))
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar()
    q = q.order_by(desc(GalleryItem.uploaded_at)).offset((page - 1) * 20).limit(20)
    result = await db.execute(q)
    items = result.scalars().all()
    return {"success": True, "gallery": [_gallery(g) for g in items], "total": total}

@gallery_router.post("/")
async def add_gallery(
    title: str = Form(...), category: str = Form(...), description: str = Form(""),
    image: UploadFile = File(...),
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    img = await save_upload_file(image)
    if not img:
        raise HTTPException(400, "Image required")
    item = GalleryItem(title=title, category=category, description=description,
                       image_path=img, uploaded_at=datetime.utcnow())
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return {"success": True, "item": _gallery(item)}

@gallery_router.delete("/{gid}")
async def delete_gallery(gid: int, user: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(GalleryItem).where(GalleryItem.id == gid))
    g = result.scalar_one_or_none()
    if not g:
        raise HTTPException(404, "Gallery item not found")
    await db.delete(g)
    await db.commit()
    return {"success": True}


# ╔══════════════════════════════════════════════════════════╗
# ║  CAMPS                                                  ║
# ╚══════════════════════════════════════════════════════════╝
camps_router = APIRouter(prefix="/api/camps", tags=["Camps"])

def _camp(c: Camp) -> dict:
    return {
        "id": c.id, "name": c.name, "location": c.location,
        "camp_type": c.camp_type, "start_date": c.start_date, "end_date": c.end_date,
        "description": c.description or "", "is_upcoming": c.is_upcoming,
        "capacity": c.capacity, "registered_count": c.registered_count,
        "created_at": c.created_at.isoformat() if isinstance(c.created_at, datetime) else ""
    }

@camps_router.get("/")
async def get_camps(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Camp).order_by(desc(Camp.start_date)))
    return {"success": True, "camps": [_camp(c) for c in result.scalars().all()]}

@camps_router.post("/")
async def create_camp(data: CampCreate, user: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    camp = Camp(**data.model_dump(), registered_count=0, created_at=datetime.utcnow())
    db.add(camp)
    await db.commit()
    await db.refresh(camp)
    return {"success": True, "camp": _camp(camp)}

@camps_router.delete("/{cid}")
async def delete_camp(cid: int, user: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Camp).where(Camp.id == cid))
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(404, "Camp not found")
    await db.delete(c)
    await db.commit()
    return {"success": True}


# ╔══════════════════════════════════════════════════════════╗
# ║  ACHIEVEMENTS                                           ║
# ╚══════════════════════════════════════════════════════════╝
achievements_router = APIRouter(prefix="/api/achievements", tags=["Achievements"])

def _ach(a: Achievement) -> dict:
    return {
        "id": a.id, "cadet_name": a.cadet_name, "title": a.title,
        "description": a.description or "", "year": a.year, "level": a.level,
        "image_url": f"/uploads/{a.image_path}" if a.image_path else None,
        "created_at": a.created_at.isoformat() if isinstance(a.created_at, datetime) else ""
    }

@achievements_router.get("/")
async def get_achievements(
    year: Optional[int] = Query(None),
    level: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    q = select(Achievement)
    if year:
        q = q.where(Achievement.year == year)
    if level and level.lower() != "all":
        q = q.where(Achievement.level.ilike(level))
    q = q.order_by(desc(Achievement.year))
    result = await db.execute(q)
    return {"success": True, "achievements": [_ach(a) for a in result.scalars().all()]}

@achievements_router.post("/")
async def create_achievement(
    cadet_name: str = Form(...), title: str = Form(...), description: str = Form(""),
    year: int = Form(...), level: str = Form(...),
    image: Optional[UploadFile] = File(None),
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    img = await save_upload_file(image) if image and image.filename else None
    ach = Achievement(cadet_name=cadet_name, title=title, description=description,
                      year=year, level=level, image_path=img, created_at=datetime.utcnow())
    db.add(ach)
    await db.commit()
    await db.refresh(ach)
    return {"success": True, "achievement": _ach(ach)}

@achievements_router.delete("/{aid}")
async def delete_achievement(aid: int, user: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Achievement).where(Achievement.id == aid))
    a = result.scalar_one_or_none()
    if not a:
        raise HTTPException(404, "Achievement not found")
    await db.delete(a)
    await db.commit()
    return {"success": True}


# ╔══════════════════════════════════════════════════════════╗
# ║  CONTACT                                                ║
# ╚══════════════════════════════════════════════════════════╝
contact_router = APIRouter(prefix="/api/contact", tags=["Contact"])

def _contact(c: ContactMessage) -> dict:
    return {
        "id": c.id, "name": c.name, "email": c.email, "phone": c.phone or "",
        "subject": c.subject, "message": c.message,
        "is_read": c.is_read,
        "created_at": c.created_at.isoformat() if isinstance(c.created_at, datetime) else ""
    }

@contact_router.post("/")
async def submit_contact(data: ContactCreate, db: AsyncSession = Depends(get_db)):
    msg = ContactMessage(**data.model_dump(), is_read=False, created_at=datetime.utcnow())
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return {"success": True, "message": "Your message has been received. We will respond within 24 hours.", "id": msg.id}

@contact_router.get("/")
async def get_contacts(user: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ContactMessage).order_by(desc(ContactMessage.created_at)))
    return {"success": True, "messages": [_contact(c) for c in result.scalars().all()]}

@contact_router.patch("/{mid}/read")
async def mark_read(mid: int, user: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ContactMessage).where(ContactMessage.id == mid))
    msg = result.scalar_one_or_none()
    if not msg:
        raise HTTPException(404, "Message not found")
    msg.is_read = True
    await db.commit()
    return {"success": True}


# ╔══════════════════════════════════════════════════════════╗
# ║  DASHBOARD / ANALYTICS                                  ║
# ╚══════════════════════════════════════════════════════════╝
dashboard_router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])

@dashboard_router.get("/stats")
async def dashboard_stats(user: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    total_cadets = (await db.execute(select(func.count()).select_from(Student))).scalar()
    pending      = (await db.execute(select(func.count()).select_from(Student).where(Student.status == "pending"))).scalar()
    approved     = (await db.execute(select(func.count()).select_from(Student).where(Student.status == "approved"))).scalar()
    rejected     = (await db.execute(select(func.count()).select_from(Student).where(Student.status == "rejected"))).scalar()
    total_notices= (await db.execute(select(func.count()).select_from(Notice))).scalar()
    total_camps  = (await db.execute(select(func.count()).select_from(Camp))).scalar()
    unread_msgs  = (await db.execute(select(func.count()).select_from(ContactMessage).where(ContactMessage.is_read == False))).scalar()
    total_achiev = (await db.execute(select(func.count()).select_from(Achievement))).scalar()
    total_gallery= (await db.execute(select(func.count()).select_from(GalleryItem))).scalar()

    recent_notices_q = await db.execute(select(Notice).order_by(desc(Notice.created_at)).limit(5))
    recent_notices = [_notice(n) for n in recent_notices_q.scalars().all()]

    recent_stu_q = await db.execute(select(Student).order_by(desc(Student.enrolled_at)).limit(5))
    from app.routes.students import _stu
    recent_students = [_stu(s) for s in recent_stu_q.scalars().all()]

    return {
        "success": True,
        "stats": {
            "total_cadets": total_cadets,
            "pending": pending, "approved": approved, "rejected": rejected,
            "total_notices": total_notices, "total_camps": total_camps,
            "unread_messages": unread_msgs, "total_achievements": total_achiev,
            "total_gallery": total_gallery
        },
        "recent_notices": recent_notices,
        "recent_students": recent_students
    }


analytics_router = APIRouter(prefix="/api/analytics", tags=["Analytics"])

@analytics_router.post("/pageview")
async def track_pageview(page: str = Form(...), db: AsyncSession = Depends(get_db)):
    from app.models.orm_models import Analytics
    entry = Analytics(page=page, timestamp=datetime.utcnow())
    db.add(entry)
    await db.commit()
    return {"success": True}

@analytics_router.get("/")
async def get_analytics(user: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    from app.models.orm_models import Analytics
    total = (await db.execute(select(func.count()).select_from(Analytics))).scalar()
    return {"success": True, "total_views": total}
