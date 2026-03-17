"""
Centralized configuration loaded from environment variables.
All settings in one place — no scattered os.getenv() calls.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/halal_trader",
)
# SQLAlchemy needs this for sync operations (Alembic)
DATABASE_URL_SYNC = DATABASE_URL.replace("+asyncpg", "").replace("asyncpg://", "postgresql://")

# ---------------------------------------------------------------------------
# Auth / JWT
# ---------------------------------------------------------------------------
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "CHANGE-ME-IN-PRODUCTION-64-chars-minimum-secret-key-here-please")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))

# ---------------------------------------------------------------------------
# Anthropic AI (server-side ONLY — never expose to frontend)
# ---------------------------------------------------------------------------
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# ---------------------------------------------------------------------------
# Stripe
# ---------------------------------------------------------------------------
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
STRIPE_PRO_MONTHLY_PRICE_ID = os.getenv("STRIPE_PRO_MONTHLY_PRICE_ID", "")
STRIPE_PRO_ANNUAL_PRICE_ID = os.getenv("STRIPE_PRO_ANNUAL_PRICE_ID", "")
STRIPE_MANAGED_MONTHLY_PRICE_ID = os.getenv("STRIPE_MANAGED_MONTHLY_PRICE_ID", "")
STRIPE_MANAGED_ANNUAL_PRICE_ID = os.getenv("STRIPE_MANAGED_ANNUAL_PRICE_ID", "")

# ---------------------------------------------------------------------------
# Encryption (Fernet) for user Schwab credentials
# ---------------------------------------------------------------------------
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "")

# ---------------------------------------------------------------------------
# Schwab API (platform-level defaults)
# ---------------------------------------------------------------------------
SCHWAB_APP_KEY = os.getenv("SCHWAB_APP_KEY", "")
SCHWAB_APP_SECRET = os.getenv("SCHWAB_APP_SECRET", "")
SCHWAB_CALLBACK_URL = os.getenv("SCHWAB_CALLBACK_URL", "https://127.0.0.1")
SCHWAB_TOKEN_PATH = os.getenv("SCHWAB_TOKEN_PATH", "schwab_token.json")

# ---------------------------------------------------------------------------
# Firebase (push notifications)
# ---------------------------------------------------------------------------
FIREBASE_SERVICE_ACCOUNT_JSON = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON", "")

# ---------------------------------------------------------------------------
# Telegram
# ---------------------------------------------------------------------------
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
TRADER_TELEGRAM_CHAT_ID = os.getenv("TRADER_TELEGRAM_CHAT_ID", "")

# ---------------------------------------------------------------------------
# Data APIs
# ---------------------------------------------------------------------------
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")
ZOYA_API_KEY = os.getenv("ZOYA_API_KEY", "")
FRED_API_KEY = os.getenv("FRED_API_KEY", "")

# ---------------------------------------------------------------------------
# Trading defaults
# ---------------------------------------------------------------------------
DRY_RUN = os.getenv("DRY_RUN", "True").lower() in ("true", "1", "yes")
AUTO_EXECUTE = os.getenv("AUTO_EXECUTE", "False").lower() in ("true", "1", "yes")
AUTO_EXECUTE_MAX_USD = float(os.getenv("AUTO_EXECUTE_MAX_USD", "50"))

# ---------------------------------------------------------------------------
# URLs
# ---------------------------------------------------------------------------
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# ---------------------------------------------------------------------------
# App identity
# ---------------------------------------------------------------------------
APP_ID = os.getenv("APP_ID", "com.halaltrader.app")
APP_NAME = os.getenv("APP_NAME", "Halal Trader")
API_PORT = int(os.getenv("API_PORT", "8000"))
API_HOST = os.getenv("API_HOST", "0.0.0.0")
