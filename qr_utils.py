"""
qr_utils.py — Time-limited, HMAC-signed QR code generation and validation.
Prevents proxy attendance by making QR codes expire after a short window.
"""
import json
import time
import hmac
import hashlib
import base64
import io
import logging

logger = logging.getLogger(__name__)

try:
    import qrcode
    from PIL import Image, ImageDraw, ImageFont
    QR_AVAILABLE = True
except ImportError:
    QR_AVAILABLE = False
    logger.warning("qrcode or Pillow not installed. QR generation unavailable.")

PARADE_GROUND_LAT = 31.6862  # Govt. Polytechnic Hamirpur (HP) — update as needed
PARADE_GROUND_LNG = 76.5213
MAX_DISTANCE_METERS = 300  # Accept QR scans within 300m of parade ground
QR_VALIDITY_SECONDS = 120  # QR expires after 2 minutes


def _sign(payload: str, secret_key: str) -> str:
    """Generate HMAC-SHA256 signature (first 16 chars)."""
    return hmac.new(
        secret_key.encode(), payload.encode(), hashlib.sha256
    ).hexdigest()[:16]


def generate_time_limited_token(user_id: int, secret_key: str, validity: int = QR_VALIDITY_SECONDS) -> str:
    """
    Generate a signed time-limited token for QR attendance.
    Format: base64(user_id:timestamp:signature)
    """
    timestamp = int(time.time())
    payload = f"{user_id}:{timestamp}"
    signature = _sign(payload, secret_key)
    token = f"{payload}:{signature}"
    return base64.urlsafe_b64encode(token.encode()).decode()


def validate_token(encoded_token: str, secret_key: str, max_age: int = QR_VALIDITY_SECONDS) -> dict:
    """
    Validate a time-limited QR token.
    Returns dict with user_id and timestamp if valid.
    Raises ValueError with descriptive message if invalid or expired.
    """
    try:
        token = base64.urlsafe_b64decode(encoded_token.encode()).decode()
        parts = token.split(':')
        if len(parts) != 3:
            raise ValueError("Invalid QR code format.")
        
        user_id_str, timestamp_str, signature = parts
        payload = f"{user_id_str}:{timestamp_str}"
        
        # Verify signature
        expected_sig = _sign(payload, secret_key)
        if not hmac.compare_digest(signature, expected_sig):
            raise ValueError("QR code signature is invalid. This code may have been tampered with.")
        
        # Check expiration
        age = time.time() - int(timestamp_str)
        if age > max_age:
            raise ValueError(f"QR code has expired (valid for {max_age} seconds). Please generate a new one.")
        
        return {'user_id': int(user_id_str), 'timestamp': int(timestamp_str), 'age_seconds': int(age)}
    
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"QR validation error: {str(e)}")


def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate distance in meters between two GPS coordinates."""
    import math
    R = 6371000  # Earth radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


def validate_location(lat: float, lng: float, max_distance: int = MAX_DISTANCE_METERS) -> dict:
    """
    Check if the given coordinates are within the allowed radius of the parade ground.
    Returns dict with is_valid, distance_meters, max_distance.
    """
    distance = haversine_distance(lat, lng, PARADE_GROUND_LAT, PARADE_GROUND_LNG)
    return {
        'is_valid': distance <= max_distance,
        'distance_meters': round(distance, 1),
        'max_distance': max_distance,
        'parade_ground': {'lat': PARADE_GROUND_LAT, 'lng': PARADE_GROUND_LNG}
    }


def generate_qr_image(token: str, cadet_name: str = 'NCC Cadet') -> io.BytesIO:
    """
    Generate a QR code PNG image for the given token.
    Returns a BytesIO buffer of the PNG image.
    """
    if not QR_AVAILABLE:
        raise RuntimeError("qrcode library not installed.")
    
    qr = qrcode.QRCode(
        version=3,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=8,
        border=3
    )
    qr.add_data(token)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color='#0d2b5e', back_color='white').convert('RGB')
    
    # Add cadet name label below QR
    width, height = img.size
    new_height = height + 50
    labeled = Image.new('RGB', (width, new_height), 'white')
    labeled.paste(img, (0, 0))
    
    draw = ImageDraw.Draw(labeled)
    try:
        font = ImageFont.truetype('arial.ttf', 16)
    except Exception:
        font = ImageFont.load_default()
    
    text = f"{cadet_name} — Valid 2 min"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    draw.text(((width - text_width) // 2, height + 10), text, fill='#0d2b5e', font=font)
    
    buf = io.BytesIO()
    labeled.save(buf, format='PNG')
    buf.seek(0)
    return buf
