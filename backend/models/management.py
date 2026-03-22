import datetime
from typing import Optional
from sqlalchemy import String, ForeignKey, DateTime, func, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB
from models.base import Base, TimestampMixin
from constants import (
    CONTACT_TYPE_KARIN,
    SCHEDULED_PAYMENT_STATUS_ACTIVE,
    OUTBOX_STATUS_PENDING
)

class Contact(Base, TimestampMixin):
    __tablename__ = "contacts"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    contact_name: Mapped[str] = mapped_column(String(100))
    contact_email: Mapped[Optional[str]] = mapped_column(String(100))
    contact_type: Mapped[str] = mapped_column(String(20), default=CONTACT_TYPE_KARIN, server_default=CONTACT_TYPE_KARIN)
    merchant_id: Mapped[Optional[str]] = mapped_column(String(50))
    subscriber_id: Mapped[Optional[str]] = mapped_column(String(100))
    bank_name: Mapped[Optional[str]] = mapped_column(String(255))
    routing_number: Mapped[Optional[str]] = mapped_column(String(9))
    account_number: Mapped[Optional[str]] = mapped_column(String(50))

    # Relationships
    user: Mapped["User"] = relationship(back_populates="contacts")

class ScheduledPayment(Base, TimestampMixin):
    __tablename__ = "scheduled_payments"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    funding_account_id: Mapped[Optional[int]] = mapped_column(ForeignKey("accounts.id"))
    recipient_email: Mapped[str] = mapped_column(String(100))
    amount: Mapped[int] = mapped_column(BigInteger)
    frequency: Mapped[str] = mapped_column(String(50))
    frequency_interval: Mapped[Optional[str]] = mapped_column(String(50))
    start_date: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True))
    end_condition: Mapped[str] = mapped_column(String(50))
    end_date: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True))
    target_payments: Mapped[Optional[int]] = mapped_column()
    payments_made: Mapped[int] = mapped_column(default=0)
    next_run_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), index=True)
    status: Mapped[str] = mapped_column(String(20), default=SCHEDULED_PAYMENT_STATUS_ACTIVE)
    retry_count: Mapped[int] = mapped_column(default=0)
    idempotency_key: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    reserve_amount: Mapped[bool] = mapped_column(default=False)
    subscriber_id: Mapped[Optional[str]] = mapped_column(String(100))

    # Relationships
    user: Mapped["User"] = relationship(back_populates="scheduled_payments")

class Outbox(Base, TimestampMixin):
    __tablename__ = "outbox"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    event_type: Mapped[str] = mapped_column(String(50))
    payload: Mapped[dict] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(20), default=OUTBOX_STATUS_PENDING, index=True)
    processed_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True))

# For relationships
from models.user import User
from models.account import Account
