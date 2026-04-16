"""
database.py — Async MySQL connection via SQLAlchemy 2.0 + aiomysql
NCC Unit – Govt. Polytechnic Hamirpur (HP)
"""

import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from dotenv import load_dotenv

load_dotenv()

MYSQL_URI: str = os.getenv(
    "MYSQL_URI",
    "mysql+aiomysql://root:password@localhost:3306/ncc_hamirpur"
)

# Async engine
engine = create_async_engine(
    MYSQL_URI,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


async def init_db():
    """Create all tables on startup."""
    from app.models.orm_models import (  # noqa: F401 — triggers table registration
        User, Student, Notice, GalleryItem, Camp, Achievement,
        ContactMessage, Analytics, CadetPoints, Event, AuditLog
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅  MySQL tables created/verified → ncc_hamirpur")


async def close_db():
    await engine.dispose()
    print("🔒  MySQL connection pool disposed.")


async def get_db():
    """FastAPI dependency — yields an async DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
