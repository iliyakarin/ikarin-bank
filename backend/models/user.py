"""User and Subscription database models.

This module defines the User and Subscription tables and their relationships.
"""
import datetime
from typing import List, Optional
from sqlalchemy import String, DateTime, func, ForeignKey, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.base import Base, TimestampMixin

class User(Base, TimestampMixin):
    """User database model.

    Stores core user information, authentication hashes, and display preferences.
    """
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    first_name: Mapped[str] = mapped_column(String(50), nullable=False)
    last_name: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    backup_email: Mapped[Optional[str]] = mapped_column(String(100), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="user", server_default="user")
    time_format: Mapped[str] = mapped_column(String(10), default="12h", server_default="12h")
    date_format: Mapped[str] = mapped_column(String(10), default="US", server_default="US")
    is_black: Mapped[bool] = mapped_column(default=False, server_default="false")

    # Relationships
    accounts: Mapped[List["Account"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    scheduled_payments: Mapped[List["ScheduledPayment"]] = relationship(back_populates="user")
    contacts: Mapped[List["Contact"]] = relationship(back_populates="user")
    subscriptions: Mapped[List["Subscription"]] = relationship(back_populates="user")

class Subscription(Base, TimestampMixin):
    """Premium subscription record.

    Tracks a user's subscription status, plan name, and expiration date.
    """
    __tablename__ = "subscriptions"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    plan_name: Mapped[str] = mapped_column(String(100), default="Karin Black")
    amount: Mapped[int] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(String(20), default="active")
    current_period_end: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True))

    # Relationships
    user: Mapped["User"] = relationship(back_populates="subscriptions")

# To support type hinting for relationships
from models.account import Account
from models.management import Contact, ScheduledPayment
