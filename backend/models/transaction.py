"""Transaction, Payment Request, and Idempotency database models.

This module defines models for recording financial movements, managing
payment requests between users, and tracking idempotency keys.
"""
import datetime
from typing import Optional
from sqlalchemy import String, ForeignKey, BigInteger, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB, UUID
from models.base import Base, TimestampMixin
from constants import TRANSACTION_STATUS_PENDING, TRANSACTION_TYPE_EXPENSE

class Transaction(Base, TimestampMixin):
    """Financial transaction database model.

    Records a single movement of funds, including metadata for auditing
    and categorization.
    """
    __tablename__ = "transactions"
    
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    parent_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)
    amount: Mapped[int] = mapped_column(BigInteger)
    category: Mapped[Optional[str]] = mapped_column(index=True)
    merchant: Mapped[Optional[str]] = mapped_column(index=True)
    status: Mapped[str] = mapped_column(default=TRANSACTION_STATUS_PENDING, index=True)
    transaction_type: Mapped[str] = mapped_column(default=TRANSACTION_TYPE_EXPENSE, index=True)
    transaction_side: Mapped[str] = mapped_column(String(10))
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))
    user_agent: Mapped[Optional[str]] = mapped_column(String(255))
    failure_reason: Mapped[Optional[str]] = mapped_column(String(255))
    commentary: Mapped[Optional[str]] = mapped_column()
    recipient_email: Mapped[Optional[str]] = mapped_column(String(100))
    sender_email: Mapped[Optional[str]] = mapped_column(String(100))
    internal_account_last_4: Mapped[Optional[str]] = mapped_column(String(4))
    subscriber_id: Mapped[Optional[str]] = mapped_column(String(100))
    payment_request_id: Mapped[Optional[int]] = mapped_column(ForeignKey("payment_requests.id"), index=True)

    # Relationships
    account: Mapped["Account"] = relationship(back_populates="transactions")

class PaymentRequest(Base, TimestampMixin):
    """Payment request database model.

    Represents a request for funds from one user to another.
    """
    __tablename__ = "payment_requests"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    requester_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    target_email: Mapped[str] = mapped_column(String(100), index=True)
    amount: Mapped[int] = mapped_column(BigInteger)
    purpose: Mapped[Optional[str]] = mapped_column()
    status: Mapped[str] = mapped_column(String(50), default="pending_target")

class IdempotencyKey(Base, TimestampMixin):
    """Idempotency key database model.

    Used to ensure that identical requests are not processed multiple times.
    """
    __tablename__ = "idempotency_keys"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    response_code: Mapped[Optional[int]] = mapped_column()
    response_body: Mapped[Optional[dict]] = mapped_column(JSONB)

# For relationships
from models.account import Account
