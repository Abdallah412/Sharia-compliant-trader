"""User model — multi-tenant, one row per user."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Boolean, Integer, Float, DateTime, Enum as SAEnum, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
import enum

from database import Base


class TierEnum(str, enum.Enum):
    free = "free"
    pro = "pro"
    managed = "managed"


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), default="")

    # Subscription
    tier: Mapped[str] = mapped_column(
        SAEnum(TierEnum, name="tier_enum", create_constraint=True),
        default=TierEnum.free,
    )
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    subscription_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    subscription_end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    trial_end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Tax settings
    income_bracket: Mapped[int] = mapped_column(Integer, default=22)
    filing_status: Mapped[str] = mapped_column(String(20), default="single")
    state: Mapped[str] = mapped_column(String(5), default="CA")

    # Trading settings (Fernet-encrypted)
    schwab_app_key_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    schwab_app_secret_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    schwab_token_json_enc: Mapped[str | None] = mapped_column(Text, nullable=True)

    dry_run: Mapped[bool] = mapped_column(Boolean, default=True)
    auto_execute: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_execute_max_usd: Mapped[float] = mapped_column(Float, default=50.0)

    # Notification settings
    telegram_chat_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    madhab_preference: Mapped[str] = mapped_column(String(20), default="aaoifi")
    zakat_anniversary_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Account state
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_trader: Mapped[bool] = mapped_column(Boolean, default=False)  # Managed tier human reviewer

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
