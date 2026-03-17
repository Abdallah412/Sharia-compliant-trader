"""Trade model — records every executed or simulated trade."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Integer, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Trade(Base):
    __tablename__ = "trades"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id"), nullable=False, index=True
    )
    ticker: Mapped[str] = mapped_column(String(10), nullable=False)
    action: Mapped[str] = mapped_column(String(10), nullable=False)  # BUY / SELL
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    total_value: Mapped[float] = mapped_column(Float, nullable=False)
    signal_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    dry_run: Mapped[bool] = mapped_column(Boolean, default=True)

    # Agent verdicts
    sheikh_verdict: Mapped[str | None] = mapped_column(String(20), nullable=True)
    finance_confidence: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tax_impact_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    holding_period_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_long_term: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    portfolio_value_after: Mapped[float | None] = mapped_column(Float, nullable=True)
    agent_reasoning: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Execution metadata
    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    approved_by: Mapped[str | None] = mapped_column(String(100), nullable=True)  # auto|user|trader:<id>
