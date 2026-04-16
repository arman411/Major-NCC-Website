import os
from dotenv import load_dotenv

# Load .env file if present (local dev)
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'ncc-gph-hamirpur-secret-key-2025')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    CERT_FOLDER   = os.path.join(BASE_DIR, 'certificates')
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024   # 10 MB
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'pdf'}

    # ── Flask-Mail (SMTP) ──────────────────────────────────────
    MAIL_SERVER   = os.environ.get('MAIL_SERVER',   'smtp.gmail.com')
    MAIL_PORT     = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS  = os.environ.get('MAIL_USE_TLS',  'true').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')          # set in .env
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')          # set in .env
    MAIL_DEFAULT_SENDER = os.environ.get(
        'MAIL_DEFAULT_SENDER', 'NCC GPH Hamirpur <noreply@gph.edu.in>')

    # ── Flask-Caching ──────────────────────────────────────────
    CACHE_TYPE    = 'SimpleCache'
    CACHE_DEFAULT_TIMEOUT = 300   # 5 minutes

    # ── Flask-Limiter ──────────────────────────────────────────
    RATELIMIT_DEFAULT = '200 per day;50 per hour'


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(BASE_DIR, 'ncc_database.db')}"


class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        f"sqlite:///{os.path.join(BASE_DIR, 'ncc_database.db')}"
    )


# Active config – switch to ProductionConfig when deploying
config = DevelopmentConfig
