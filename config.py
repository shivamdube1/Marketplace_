"""
FabricBazaar configuration.

All secrets MUST come from environment variables — never hardcode credentials.
Copy .env.example to .env and fill in real values before running.
"""
import os
import secrets
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def _require_env(key: str, fallback: str | None = None) -> str:
    """Return env var or fallback; raise in production if missing."""
    value = os.environ.get(key, fallback)
    if value is None:
        raise RuntimeError(
            f"Required environment variable '{key}' is not set. "
            f"Copy .env.example to .env and fill it in."
        )
    return value


class Config:
    # ── Core ──────────────────────────────────────────────────────────────────
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # 1 hour

    # ── Security headers ──────────────────────────────────────────────────────
    SESSION_COOKIE_HTTPONLY  = True
    SESSION_COOKIE_SAMESITE  = 'Lax'
    PERMANENT_SESSION_LIFETIME = 86400  # 24 hours

    # ── Uploads ───────────────────────────────────────────────────────────────
    UPLOAD_FOLDER        = os.path.join(BASE_DIR, 'static', 'images')
    ALLOWED_EXTENSIONS   = {'png', 'jpg', 'jpeg', 'webp'}
    MAX_CONTENT_LENGTH   = 5 * 1024 * 1024   # 5 MB

    # ── Pagination ────────────────────────────────────────────────────────────
    PRODUCTS_PER_PAGE = 12

    # ── Branding ──────────────────────────────────────────────────────────────
    BRAND_NAME     = 'FabricBazaar'
    BRAND_TAGLINE  = "India's Fabric Marketplace"
    CURRENCY       = 'INR'
    CURRENCY_SYMBOL = '₹'

    # ── Razorpay ─────────────────────────────────────────────────────────────
    # Keys are loaded from environment — NEVER hardcode here.
    RAZORPAY_KEY_ID     = os.environ.get('RAZORPAY_KEY_ID', '')
    RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET', '')
    RAZORPAY_UPI_ID     = os.environ.get('RAZORPAY_UPI_ID', '')

    # ── COD fraud prevention ──────────────────────────────────────────────────
    COD_MAX_ORDER_VALUE = 5000   # orders above ₹5000 must pay online
    COD_MAX_PENDING     = 2      # max undelivered COD orders per user


class DevelopmentConfig(Config):
    DEBUG = True
    SESSION_COOKIE_SECURE = False
    SQLALCHEMY_DATABASE_URI = (
        os.environ.get('DATABASE_URL') or
        f'sqlite:///{os.path.join(BASE_DIR, "fabricbazaar_dev.db")}'
    )
    # Relaxed Razorpay check in dev — allow empty test keys
    RAZORPAY_KEY_ID     = os.environ.get('RAZORPAY_KEY_ID', '')  # Set in .env
    RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET', '')  # Set in .env


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True   # HTTPS only
    SQLALCHEMY_DATABASE_URI = (
        os.environ.get('DATABASE_URL') or
        # PostgreSQL preferred in production; falls back to SQLite only for
        # initial setup convenience — switch to Postgres ASAP.
        f'sqlite:///{os.path.join(BASE_DIR, "fabricbazaar_prod.db")}'
    )

    @classmethod
    def init_app(cls, app):
        # Warn loudly if production is using SQLite
        db_url = cls.SQLALCHEMY_DATABASE_URI
        if 'sqlite' in db_url:
            import warnings
            warnings.warn(
                "⚠️  Production is using SQLite. Set DATABASE_URL to a "
                "PostgreSQL connection string for production use.",
                RuntimeWarning, stacklevel=2,
            )
        # Warn if placeholder Razorpay keys still present
        if not cls.RAZORPAY_KEY_ID:
            import warnings
            warnings.warn(
                "⚠️  RAZORPAY_KEY_ID is not set. Online payments will fail.",
                RuntimeWarning, stacklevel=2,
            )


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    SESSION_COOKIE_SECURE = False


config = {
    'development': DevelopmentConfig,
    'production':  ProductionConfig,
    'testing':     TestingConfig,
    'default':     DevelopmentConfig,
}
