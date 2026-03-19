"""consolidate_initialization

Revision ID: f3e8b1d2c3f4
Revises: 9c37a5071631
Create Date: 2026-03-17 19:24:47.972626

"""
from typing import Sequence, Union
import logging

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector
import clickhouse_connect
from passlib.context import CryptContext

# Import settings from the application
import sys
import os
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '..', '..')))
from config import settings

# revision identifiers, used by Alembic.
revision: str = 'f3e8b1d2c3f4'
down_revision: Union[str, Sequence[str], None] = '9c37a5071631'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

logger = logging.getLogger('alembic.runtime.migration')
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_tables = inspector.get_table_names()

    # 1. PostgreSQL Structural Migrations (Idempotent)
    logger.info("🐘 Starting PostgreSQL migrations...")

    # 1.1 Users table
    if "users" in existing_tables:
        columns = [c["name"] for c in inspector.get_columns("users")]
        if "time_format" not in columns:
            op.add_column('users', sa.Column('time_format', sa.String(length=10), server_default='12h', nullable=False))
        if "date_format" not in columns:
            op.add_column('users', sa.Column('date_format', sa.String(length=10), server_default='US', nullable=False))
        if "is_black" not in columns:
            op.add_column('users', sa.Column('is_black', sa.Boolean(), server_default='false', nullable=False))

    # 1.2 Contacts table
    if "contacts" in existing_tables:
        columns = [c["name"] for c in inspector.get_columns("contacts")]
        if "contact_type" not in columns:
            op.add_column('contacts', sa.Column('contact_type', sa.String(length=20), server_default='karin', nullable=False))
        if "merchant_id" not in columns:
            op.add_column('contacts', sa.Column('merchant_id', sa.String(length=50), nullable=True))
        if "subscriber_id" not in columns:
            op.add_column('contacts', sa.Column('subscriber_id', sa.String(length=100), nullable=True))
        if "bank_name" not in columns:
            op.add_column('contacts', sa.Column('bank_name', sa.String(length=255), nullable=True))
        if "routing_number" not in columns:
            op.add_column('contacts', sa.Column('routing_number', sa.String(length=9), nullable=True))
        if "account_number" not in columns:
            op.add_column('contacts', sa.Column('account_number', sa.String(length=50), nullable=True))

    # 1.3 Accounts table
    if "accounts" in existing_tables:
        columns = [c["name"] for c in inspector.get_columns("accounts")]
        if "is_main" not in columns:
            op.add_column('accounts', sa.Column('is_main', sa.Boolean(), server_default='true', nullable=False))
        if "parent_account_id" not in columns:
            op.add_column('accounts', sa.Column('parent_account_id', sa.Integer(), nullable=True))
            op.create_foreign_key('fk_accounts_parent_account_id', 'accounts', 'accounts', ['parent_account_id'], ['id'])
        if "name" not in columns:
            op.add_column('accounts', sa.Column('name', sa.String(length=100), server_default='Main Account', nullable=False))

    # 1.4 Transactions table
    if "transactions" in existing_tables:
        columns = [c["name"] for c in inspector.get_columns("transactions")]
        if "commentary" not in columns:
            op.add_column('transactions', sa.Column('commentary', sa.String(), nullable=True))
        if "subscriber_id" not in columns:
            op.add_column('transactions', sa.Column('subscriber_id', sa.String(length=100), nullable=True))
        if "internal_account_last_4" not in columns:
            op.add_column('transactions', sa.Column('internal_account_last_4', sa.String(length=4), nullable=True))
        if "sender_email" not in columns:
            op.add_column('transactions', sa.Column('sender_email', sa.String(length=100), nullable=True))
        if "recipient_email" not in columns:
            op.add_column('transactions', sa.Column('recipient_email', sa.String(length=100), nullable=True))
        if "payment_request_id" not in columns:
            op.add_column('transactions', sa.Column('payment_request_id', sa.Integer(), sa.ForeignKey('payment_requests.id'), nullable=True))
            op.create_index('ix_transactions_payment_request_id', 'transactions', ['payment_request_id'])

    # 1.5 Scheduled Payments table
    if "scheduled_payments" in existing_tables:
        columns = [c["name"] for c in inspector.get_columns("scheduled_payments")]
        if "funding_account_id" not in columns:
            op.add_column('scheduled_payments', sa.Column('funding_account_id', sa.Integer(), sa.ForeignKey('accounts.id'), nullable=True))
        if "subscriber_id" not in columns:
            op.add_column('scheduled_payments', sa.Column('subscriber_id', sa.String(length=100), nullable=True))

    # 2. ClickHouse Migrations (Sync)
    logger.info("🚀 Starting ClickHouse migrations...")
    try:
        ch_client = clickhouse_connect.get_client(
            host=settings.CLICKHOUSE_HOST,
            port=settings.CLICKHOUSE_PORT,
            username=settings.CLICKHOUSE_USER,
            password=settings.CLICKHOUSE_PASSWORD
        )
        ch_client.command(f"CREATE DATABASE IF NOT EXISTS {settings.CLICKHOUSE_DB}")

        # Activity Events Table
        ch_client.command(f"""
            CREATE TABLE IF NOT EXISTS {settings.CLICKHOUSE_DB}.activity_events (
                event_id        String,
                user_id         Int64,
                category        LowCardinality(String),
                action          LowCardinality(String),
                event_time      DateTime,
                title           String,
                details         String
            ) ENGINE = ReplacingMergeTree()
            PARTITION BY toYYYYMM(event_time)
            ORDER BY (user_id, event_time, event_id);
        """)

        # Transactions Table
        ch_client.command(f"""
            CREATE TABLE IF NOT EXISTS {settings.CLICKHOUSE_DB}.transactions (
                transaction_id String,
                parent_id Nullable(String),
                account_id Int64,
                sender_email Nullable(String),
                recipient_email Nullable(String),
                amount Float64,
                category String,
                merchant String,
                transaction_type String,
                transaction_side String,
                event_time DateTime,
                internal_account_last_4 Nullable(String),
                subscriber_id Nullable(String),
                failure_reason Nullable(String),
                status String DEFAULT 'cleared'
            ) ENGINE = ReplacingMergeTree()
            PARTITION BY toYYYYMM(event_time)
            ORDER BY (account_id, event_time, transaction_id);
        """)
        logger.info("✅ ClickHouse migrations complete.")
    except Exception as e:
        logger.warning(f"⚠️ ClickHouse migration skipped or failed: {e}")

    # 3. Seed Admin User
    logger.info("👤 Seeding admin user...")
    admin_email = settings.ADMIN_EMAIL
    admin_password = settings.ADMIN_PASSWORD
    if admin_email and admin_password:
        password_hash = pwd_context.hash(admin_password)
        # Check if user exists using SQL directly as we are in a migration
        res = conn.execute(sa.text("SELECT id FROM users WHERE email = :email"), {"email": admin_email}).fetchone()
        if res:
            logger.info("Admin user exists. Updating role and password.")
            conn.execute(sa.text("UPDATE users SET role = 'admin', password_hash = :hash WHERE email = :email"),
                         {"hash": password_hash, "email": admin_email})
        else:
            logger.info("Creating new admin user.")
            conn.execute(sa.text("INSERT INTO users (first_name, last_name, email, password_hash, role) VALUES ('Admin', 'System', :email, :hash, 'admin')"),
                         {"email": admin_email, "hash": password_hash})

    logger.info("✅ Consolidation complete.")


def downgrade() -> None:
    """Downgrade schema (optional, usually not needed for init consolidation)."""
    pass
