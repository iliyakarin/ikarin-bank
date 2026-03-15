import asyncio
import os
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text, select
from passlib.context import CryptContext
import clickhouse_connect

# Local imports
from database import User, Base, engine as pg_engine

logger = logging.getLogger(__name__)

# ClickHouse Configuration
CH_HOST = os.getenv("CLICKHOUSE_HOST")
CH_PORT = int(os.getenv("CLICKHOUSE_PORT", 8123))
CH_USER = os.getenv("CLICKHOUSE_USER")
CH_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD")
CH_DB = os.getenv("CLICKHOUSE_DB")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SessionLocal = async_sessionmaker(bind=pg_engine, class_=AsyncSession)

async def run_postgres_migrations():
    """Runs PostgreSQL schema updates idempotently."""
    logger.info("🐘 Starting PostgreSQL migrations...")
    async with pg_engine.begin() as conn:
        # 1. users table
        await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS time_format VARCHAR(10) DEFAULT '12h' NOT NULL"))
        await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS date_format VARCHAR(10) DEFAULT 'US' NOT NULL"))
        await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_black BOOLEAN DEFAULT FALSE NOT NULL"))
        
        # 2. contacts table
        await conn.execute(text("ALTER TABLE contacts ADD COLUMN IF NOT EXISTS contact_type VARCHAR(20) DEFAULT 'karin' NOT NULL"))
        await conn.execute(text("ALTER TABLE contacts ADD COLUMN IF NOT EXISTS merchant_id VARCHAR(50)"))
        await conn.execute(text("ALTER TABLE contacts ADD COLUMN IF NOT EXISTS subscriber_id VARCHAR(100)"))
        await conn.execute(text("ALTER TABLE contacts ADD COLUMN IF NOT EXISTS bank_name VARCHAR(255)"))
        await conn.execute(text("ALTER TABLE contacts ADD COLUMN IF NOT EXISTS routing_number VARCHAR(9)"))
        await conn.execute(text("ALTER TABLE contacts ADD COLUMN IF NOT EXISTS account_number VARCHAR(50)"))
        
        # 3. accounts table
        await conn.execute(text("ALTER TABLE accounts ADD COLUMN IF NOT EXISTS is_main BOOLEAN DEFAULT TRUE NOT NULL"))
        await conn.execute(text("ALTER TABLE accounts ADD COLUMN IF NOT EXISTS parent_account_id INTEGER REFERENCES accounts(id)"))
        await conn.execute(text("ALTER TABLE accounts ADD COLUMN IF NOT EXISTS name VARCHAR(100) DEFAULT 'Main Account' NOT NULL"))
        
        # 4. transactions table
        await conn.execute(text("ALTER TABLE transactions ADD COLUMN IF NOT EXISTS commentary TEXT"))
        await conn.execute(text("ALTER TABLE transactions ADD COLUMN IF NOT EXISTS subscriber_id VARCHAR(100)"))
        await conn.execute(text("ALTER TABLE transactions ADD COLUMN IF NOT EXISTS internal_account_last_4 VARCHAR(4)"))
        await conn.execute(text("ALTER TABLE transactions ADD COLUMN IF NOT EXISTS sender_email VARCHAR(100)"))
        await conn.execute(text("ALTER TABLE transactions ADD COLUMN IF NOT EXISTS recipient_email VARCHAR(100)"))
        # payment_request_id might fail if payment_requests table doesn't exist yet, but Base.metadata.create_all handles table creation first
        try:
            await conn.execute(text("ALTER TABLE transactions ADD COLUMN IF NOT EXISTS payment_request_id INTEGER REFERENCES payment_requests(id)"))
        except Exception as e:
            logger.warning(f"⚠️ Could not add payment_request_id to transactions (maybe table missing?): {e}")
        
        # 5. scheduled_payments table
        await conn.execute(text("ALTER TABLE scheduled_payments ADD COLUMN IF NOT EXISTS funding_account_id INTEGER REFERENCES accounts(id)"))
        await conn.execute(text("ALTER TABLE scheduled_payments ADD COLUMN IF NOT EXISTS subscriber_id VARCHAR(100)"))

        # 6. Standardization: Convert all timestamp columns to WITH TIME ZONE
        # This fixes the "can't subtract offset-naive and offset-aware datetimes" errors
        tables_to_fix = {
            "users": ["created_at"],
            "scheduled_payments": ["start_date", "end_date", "next_run_at"],
            "payment_requests": ["created_at", "updated_at"],
            "contacts": ["created_at"],
            "transactions": ["created_at"],
            "idempotency_keys": ["created_at"],
            "outbox": ["created_at", "processed_at"]
        }
        
        for table, columns in tables_to_fix.items():
            for col in columns:
                try:
                    await conn.execute(text(f"ALTER TABLE {table} ALTER COLUMN {col} TYPE TIMESTAMP WITH TIME ZONE USING {col} AT TIME ZONE 'UTC'"))
                except Exception as e:
                    logger.warning(f"⚠️ Could not convert {table}.{col} to TZ-aware: {e}")
        
    logger.info("✅ PostgreSQL column checks complete.")

async def setup_admin_user():
    """Ensures the admin user exists and has the correct role/password."""
    admin_email = os.getenv("ADMIN_EMAIL")
    admin_password = os.getenv("ADMIN_PASSWORD")
    
    if not admin_email or not admin_password:
        logger.warning("⚠️ Skipping admin user setup: ADMIN_EMAIL or ADMIN_PASSWORD not set in environment.")
        return
    
    async with SessionLocal() as db:
        logger.info(f"👤 Checking admin user: {admin_email}")
        result = await db.execute(select(User).filter(User.email == admin_email))
        user = result.scalars().first()
        
        if user:
            logger.info("Admin user exists. Refreshing role and password.")
            user.role = "admin"
            user.password_hash = pwd_context.hash(admin_password)
        else:
            logger.info("Creating new admin user.")
            user = User(
                first_name="Admin",
                last_name="System",
                email=admin_email,
                password_hash=pwd_context.hash(admin_password),
                role="admin"
            )
            db.add(user)
        
        await db.commit()
    logger.info("✅ Admin user synchronization complete.")

def run_clickhouse_migrations():
    """Runs ClickHouse schema updates idempotently."""
    logger.info("🚀 Starting ClickHouse migrations...")
    try:
        client = clickhouse_connect.get_client(
            host=CH_HOST, port=CH_PORT, username=CH_USER, password=CH_PASSWORD
        )
        
        # Ensure database exists
        client.command(f"CREATE DATABASE IF NOT EXISTS {CH_DB}")

        # 1. Activity Events Table
        client.command(f"""
            CREATE TABLE IF NOT EXISTS {CH_DB}.activity_events (
                event_id        String,
                user_id         Int64,
                category        LowCardinality(String),
                action          LowCardinality(String),
                event_time      DateTime,
                title           String,
                details         String
            ) ENGINE = MergeTree()
            PARTITION BY toYYYYMM(event_time)
            ORDER BY (user_id, event_time, event_id)
        """)
        logger.info(f"✅ Verified {CH_DB}.activity_events table")

        # 2. Transactions Table
        table_exists = client.command(f"EXISTS TABLE {CH_DB}.transactions")
        
        if table_exists:
            client.command(f"""
                ALTER TABLE {CH_DB}.transactions 
                ADD COLUMN IF NOT EXISTS parent_id Nullable(String),
                ADD COLUMN IF NOT EXISTS account_id Int64,
                ADD COLUMN IF NOT EXISTS sender_email Nullable(String),
                ADD COLUMN IF NOT EXISTS merchant String,
                ADD COLUMN IF NOT EXISTS transaction_type String,
                ADD COLUMN IF NOT EXISTS transaction_side String,
                ADD COLUMN IF NOT EXISTS event_time DateTime DEFAULT now(),
                ADD COLUMN IF NOT EXISTS category String,
                ADD COLUMN IF NOT EXISTS internal_account_last_4 Nullable(String),
                ADD COLUMN IF NOT EXISTS subscriber_id Nullable(String),
                ADD COLUMN IF NOT EXISTS failure_reason Nullable(String)
            """)
            logger.info(f"✅ Synchronized {CH_DB}.transactions columns")
        else:
            client.command(f"""
                CREATE TABLE {CH_DB}.transactions (
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
                    status String
                ) ENGINE = ReplacingMergeTree()
                PARTITION BY toYYYYMM(event_time)
                ORDER BY (account_id, event_time, transaction_id)
            """)
            logger.info(f"✅ Created {CH_DB}.transactions table")
            
    except Exception as e:
        logger.error(f"❌ ClickHouse migration failed: {e}")
        # We don't necessarily want to crash the whole app if CH is down, but we log it
    
    logger.info("✅ ClickHouse migrations complete.")

async def run_all_migrations():
    """Main entry point for startup migrations."""
    # 1. PostgreSQL Structural Migrations
    await run_postgres_migrations()
    
    # 2. Admin User Sync
    await setup_admin_user()
    
    # 3. ClickHouse Migrations (Sync)
    run_clickhouse_migrations()

if __name__ == "__main__":
    # Allow running as a standalone script for testing
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_all_migrations())
