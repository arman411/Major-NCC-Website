"""
qr_utils.py — NCC Website
QR Code generation utilities for the NCC Cadet Attendance System.

Each cadet gets a unique, HMAC-signed QR code that cannot be forged.
When scanned by the ANO/SUO, it marks the cadet as present for today.

Exports:
  • generate_cadet_qr(student, secret_key) → BytesIO PNG image stream
  • validate_qr_token(token, secret_key)   → student_id (int) or raises ValueError
"""

import io
import hmac
import hashlib
import json
import base64
from datetime import datetime

try:
    import qrcode # type: ignore
    from qrcode.image.styles.moduledrawers import RoundedModuleDrawer # type: ignore
    from qrcode.image.styledpil import StyledPilImage # type: ignore
    QR_AVAILABLE = True
except ImportError:
    QR_AVAILABLE = False

try:
    from PIL import Image, ImageDraw # type: ignore
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


def _sign_payload(payload: dict, secret_key: str) -> str:
    """Create an HMAC-SHA256 signature for a dict payload."""
    payload_bytes = json.dumps(payload, separators=(',', ':')).encode()
    sig = hmac.new(secret_key.encode(), payload_bytes, hashlib.sha256).hexdigest()
    return sig


def generate_cadet_qr(student, secret_key: str) -> io.BytesIO:
    """
    Generate a signed QR code PNG for a cadet.

    The QR encodes a JSON token:
    {
        "id": <student.id>,
        "roll": "<roll_no>",
        "sig": "<hmac-sha256 of id+roll>"
    }

    Returns a BytesIO PNG image stream.
    Raises RuntimeError if the qrcode library is not installed.
    """
    if not QR_AVAILABLE:
        raise RuntimeError("qrcode library not installed. Run: pip install qrcode[pil]")

    payload = {
        "id":   student.id,
        "roll": student.roll_no,
        "name": f"{student.first_name} {student.last_name}",
    }
    payload["sig"] = _sign_payload({"id": student.id, "roll": student.roll_no}, secret_key)
    token = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()

    # Create QR code with rounded style
    qr = qrcode.QRCode(
        version=3,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=3,
    )
    qr.add_data(token)
    qr.make(fit=True)

    try:
        img = qr.make_image(
            image_factory=StyledPilImage,
            module_drawer=RoundedModuleDrawer(),
        )
    except Exception:
        # Fall back to standard image if styled PIL not available
        img = qr.make_image(fill_color="#0D2B5E", back_color="white")

    # Add cadet info banner below QR
    if PIL_AVAILABLE:
        qr_img = img.convert("RGBA")
        banner_h = 60
        full_img = Image.new("RGBA", (qr_img.width, qr_img.height + banner_h), (13, 43, 94, 255))
        full_img.paste(qr_img, (0, 0))

        draw = ImageDraw.Draw(full_img)
        try:
            # Try to load a system font
            from PIL import ImageFont
            font_name = ImageFont.load_default(size=14)
            font_small = ImageFont.load_default(size=11)
        except Exception:
            font_name  = None
            font_small = None

        name_text = f"{student.first_name} {student.last_name}"
        roll_text = f"Roll: {student.roll_no}  |  {student.ncc_wing} Wing"

        # Draw name and roll_no
        draw.text((10, qr_img.height + 8),  name_text, fill="white", font=font_name)
        draw.text((10, qr_img.height + 34), roll_text, fill="#A9CCE3", font=font_small)

        buf = io.BytesIO()
        full_img.save(buf, format="PNG")
        buf.seek(0)
        return buf
    else:
        buf = io.BytesIO()
        img.save(buf)
        buf.seek(0)
        return buf


def validate_qr_token(token: str, secret_key: str) -> dict:
    """
    Decode and validate a QR token scanned from a cadet's QR code.

    Returns a dict with: {"id": <int>, "roll": "<str>", "name": "<str>"}
    Raises ValueError if the token is invalid or has been tampered with.
    """
    try:
        payload = json.loads(base64.urlsafe_b64decode(token.encode()))
    except Exception:
        raise ValueError("Invalid QR token format.")

    for key in ("id", "roll", "sig"):
        if key not in payload:
            raise ValueError(f"QR token missing field: {key}")

    # Re-compute expected signature
    expected_sig = _sign_payload({"id": payload["id"], "roll": payload["roll"]}, secret_key)

    # Constant-time comparison to prevent timing attacks
    if not hmac.compare_digest(payload["sig"], expected_sig):
        raise ValueError("QR token signature is invalid. Possible tampering detected.")

    return {
        "id":   int(payload["id"]),
        "roll": payload["roll"],
        "name": payload.get("name", ""),
    }
