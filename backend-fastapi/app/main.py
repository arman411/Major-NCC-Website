"""
main.py — FastAPI application entry point
NCC Unit – Govt. Polytechnic Hamirpur (HP)
Backend: Python + FastAPI | Database: MySQL + SQLAlchemy
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

load_dotenv()

from app.database import init_db, close_db
from app.routes.auth import router as auth_router
from app.routes.students import router as students_router
from app.routes.events import router as events_router
from app.routes.certificates import router as certificates_router
from app.routes.api import (
    notices_router, gallery_router, camps_router,
    achievements_router, contact_router, dashboard_router,
    analytics_router, leaderboard_router, stats_router
)

ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:5500,http://localhost:5500,http://localhost:8080"
).split(",")
DEBUG = os.getenv("DEBUG", "true").lower() == "true"
UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads")

# ── Rate limiter ──────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=["500/day", "100/hour"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()               # Create MySQL tables
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    # Seed initial data if tables are empty
    try:
        from app.utils.seed import seed_initial_data
        await seed_initial_data()
    except Exception as e:
        print(f"Seeding skipped: {e}")
    yield
    await close_db()


# ── App initialization ────────────────────────────────────────────────────────
app = FastAPI(
    title="NCC Unit API – Govt. Polytechnic Hamirpur (HP)",
    description="REST API for NCC website. Stack: FastAPI + MySQL + SQLAlchemy.",
    version="3.0.0",
    docs_url="/docs" if DEBUG else None,
    redoc_url="/redoc" if DEBUG else None,
    lifespan=lifespan
)

# ── CORS ──────────────────────────────────────────────────────────────────────
# In DEBUG mode allow all origins (file:// opened pages, Live Server, etc.)
# In production restrict to ALLOWED_ORIGINS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if DEBUG else ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Rate limiting ─────────────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── Static files (uploads) ────────────────────────────────────────────────────
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_FOLDER), name="uploads")

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(students_router)
app.include_router(events_router)
app.include_router(certificates_router)
app.include_router(notices_router)
app.include_router(gallery_router)
app.include_router(camps_router)
app.include_router(achievements_router)
app.include_router(contact_router)
app.include_router(dashboard_router)
app.include_router(analytics_router)
app.include_router(leaderboard_router)
app.include_router(stats_router)


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok", "app": "NCC GPH Hamirpur API", "version": "3.0.0", "db": "MySQL"}


@app.get("/")
async def root():
    return {"message": "NCC Unit – Govt. Polytechnic Hamirpur (HP) API v3.0", "docs": "/docs"}
