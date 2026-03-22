"""Financial Account and Payment Method database models.

This module defines the Account and PaymentMethod tables, including support
for sub-accounts and encrypted payment credentials.
"""
import datetime
from typing import List, Optional
from sqlalchemy import String, ForeignKey, BigInteger, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.base import Base, TimestampMixin

class Account(Base, TimestampMixin):
    """Financial account database model.

    Represents a bank account (main or sub-account) with balance tracking
    and associated credentials.
    """
    __tablename__ = "accounts"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    is_main: Mapped[bool] = mapped_column(default=True, server_default="true")
    parent_account_id: Mapped[Optional[int]] = mapped_column(ForeignKey("accounts.id"))
    name: Mapped[str] = mapped_column(String(100), default="Main Account", server_default="Main Account")
    balance: Mapped[int] = mapped_column(BigInteger, default=0)
    reserved_balance: Mapped[int] = mapped_column(BigInteger, default=0)

    # Account Credentials
    routing_number: Mapped[Optional[str]] = mapped_column(String(9))
    account_number_encrypted: Mapped[Optional[str]] = mapped_column(String(255))
    account_number_last_4: Mapped[Optional[str]] = mapped_column(String(4))
    internal_reference_id: Mapped[Optional[str]] = mapped_column(String(100), unique=True, index=True)
    account_uuid: Mapped[Optional[str]] = mapped_column(String(36), unique=True, index=True)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="accounts")
    transactions: Mapped[List["Transaction"]] = relationship(back_populates="account")
    payment_methods: Mapped[List["PaymentMethod"]] = relationship(back_populates="account")

class PaymentMethod(Base, TimestampMixin):
    """Payment method (e.g., credit/debit card) database model.

    Stores encrypted card information linked to a bank account.
    """
    __tablename__ = "payment_methods"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    gateway_pm_id: Mapped[Optional[str]] = mapped_column(String(100), unique=True, index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)

    # Encrypted sensitive data
    card_number_encrypted: Mapped[str] = mapped_column(String(255))
    expiry_date_encrypted: Mapped[str] = mapped_column(String(255))
    cvc_encrypted: Mapped[str] = mapped_column(String(255))
    cardholder_name_encrypted: Mapped[str] = mapped_column(String(255))

    # Safe display data
    card_last_4: Mapped[str] = mapped_column(String(4))
    card_brand: Mapped[str] = mapped_column(String(20), default="unknown")

    # Relationships
    account: Mapped["Account"] = relationship(back_populates="payment_methods")

# To support type hinting for relationships
from models.user import User
from models.transaction import Transaction
