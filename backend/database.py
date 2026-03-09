import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import declarative_base
import datetime

# Database Configuration
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_PORT = os.getenv("POSTGRES_PORT")

if not all([POSTGRES_USER, POSTGRES_DB, POSTGRES_HOST, POSTGRES_PORT]):
    # Note: password might be empty in some dev setups, but others are required
    print("[WARNING] Missing database environment variables. Application may fail to connect.")

DATABASE_URL = f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

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
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    backup_email = Column(String(100), unique=True, index=True, nullable=True)
    password_hash = Column(String(255), nullable=False)
    # Use server_default to ensure existing rows get a value during migration
    role = Column(String(20), default="user", server_default="user", nullable=False)
    time_format = Column(String(10), default="12h", server_default="12h", nullable=False)
    date_format = Column(String(10), default="US", server_default="US", nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Account(Base):
    __tablename__ = "accounts"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    is_main = Column(Boolean, default=True, server_default="true", nullable=False)
    parent_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    name = Column(String(100), default="Main Account", server_default="Main Account", nullable=False)
    balance = Column(Numeric(15, 2), default=0.00)
    reserved_balance = Column(Numeric(15, 2), default=0.00)
    
    # Account Credentials
    routing_number = Column(String(9), nullable=True)
    account_number_encrypted = Column(String(255), nullable=True)
    account_number_last_4 = Column(String(4), nullable=True)
    internal_reference_id = Column(String(100), unique=True, index=True, nullable=True)

class ScheduledPayment(Base):
    __tablename__ = "scheduled_payments"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    funding_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True) # Allows targeting sub-accounts
    recipient_email = Column(String(100), nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)
    frequency = Column(String(50), nullable=False)
    frequency_interval = Column(String(50), nullable=True)
    start_date = Column(DateTime, nullable=False)
    end_condition = Column(String(50), nullable=False)
    end_date = Column(DateTime, nullable=True)
    target_payments = Column(Integer, nullable=True)
    payments_made = Column(Integer, default=0, nullable=False)
    next_run_at = Column(DateTime, index=True, nullable=True)
    status = Column(String(20), default="Active", nullable=False)
    retry_count = Column(Integer, default=0, nullable=False)
    idempotency_key = Column(String(100), unique=True, index=True, nullable=False)
    reserve_amount = Column(Boolean, default=False, nullable=False)
    subscriber_id = Column(String(100), nullable=True) # For Vendor Payments

class PaymentRequest(Base):
    __tablename__ = "payment_requests"
    id = Column(Integer, primary_key=True, index=True)
    requester_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    target_email = Column(String(100), index=True, nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)
    purpose = Column(String, nullable=True)
    status = Column(String(50), default="pending_target", nullable=False) # pending_target, pending_requester, paid, declined, cancelled
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

class Contact(Base):
    __tablename__ = "contacts"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    contact_name = Column(String(100), nullable=False)
    contact_email = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

from sqlalchemy.dialects.postgresql import JSONB, UUID

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(UUID(as_uuid=False), primary_key=True) # UUID generated by API
    parent_id = Column(UUID(as_uuid=False), index=True, nullable=True) # Links Debit/Credit pairs
    account_id = Column(Integer, ForeignKey("accounts.id"), index=True)
    amount = Column(Numeric(15, 2))
    category = Column(String)
    merchant = Column(String)
    status = Column(String, default="pending") # pending, sent_to_kafka, cleared
    transaction_type = Column(String, default="expense") # expense, income, transfer
    transaction_side = Column(String(10)) # DEBIT or CREDIT
    idempotency_key = Column(String(100), index=True)
    ip_address = Column(String(45))
    user_agent = Column(String(255))
    failure_reason = Column(String(255))
    commentary = Column(String, nullable=True)
    subscriber_id = Column(String(100), nullable=True) # For Vendor Payments
    payment_request_id = Column(Integer, ForeignKey("payment_requests.id"), index=True, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)





class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"
    id = Column(Integer, primary_key=True)
    key = Column(String(100), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    response_code = Column(Integer)
    response_body = Column(JSONB)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Outbox(Base):
    __tablename__ = "outbox"
    id = Column(Integer, primary_key=True)
    event_type = Column(String(50), nullable=False)
    payload = Column(JSONB, nullable=False)

    status = Column(String(20), default="pending")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
