"""
utils/upload.py — File upload utility for NCC uploads directory
"""

import os
import uuid
import aiofiles
from fastapi import UploadFile
from dotenv import load_dotenv

load_dotenv()

UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads")
MAX_SIZE_MB    = int(os.getenv("MAX_UPLOAD_SIZE_MB", "10"))
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
ALLOWED_ALL_TYPES   = ALLOWED_IMAGE_TYPES | {"application/pdf"}


async def save_upload_file(upload: UploadFile, allow_pdf: bool = True) -> str | None:
    """Save an uploaded file and return its relative filename (stored under UPLOAD_FOLDER)."""
    if not upload or not upload.filename:
        return None

    # Validate MIME type
    allowed = ALLOWED_ALL_TYPES if allow_pdf else ALLOWED_IMAGE_TYPES
    if upload.content_type not in allowed:
        return None

    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    ext = os.path.splitext(upload.filename)[-1].lower()
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)

    content = await upload.read()
    if len(content) > MAX_SIZE_MB * 1024 * 1024:
        return None

    async with aiofiles.open(filepath, "wb") as f:
        await f.write(content)

    return filename
