"""Database connection and session management.

This module initializes the SQLAlchemy async engine and provides the
SessionLocal factory for creating database sessions.
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from config import settings
from models.base import Base
from models.user import User, Subscription
from models.account import Account, PaymentMethod
from models.transaction import Transaction, PaymentRequest, IdempotencyKey
from models.management import Contact, ScheduledPayment, Outbox

# Database Configuration
DATABASE_URL = settings.DATABASE_URL

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    pool_size=20,
    max_overflow=10
)

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False
)

# Re-exporting for backward compatibility during transition
__all__ = [
    "Base", "User", "Subscription", "Account", "PaymentMethod",
    "Transaction", "PaymentRequest", "IdempotencyKey", 
    "Contact", "ScheduledPayment", "Outbox",
    "engine", "SessionLocal"
]
