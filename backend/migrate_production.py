import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text, select
from passlib.context import CryptContext
from database import User, Base

# Database Configuration (matching database.py)
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_PORT = os.getenv("POSTGRES_PORT")

DATABASE_URL = f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

engine = create_async_engine(DATABASE_URL)
SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def migrate():
    async with engine.begin() as conn:
        print("🚀 Starting database migration...")
        
        # 1. users table
        print("Checking 'users' table...")
        await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS time_format VARCHAR(10) DEFAULT '12h' NOT NULL"))
        await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS date_format VARCHAR(10) DEFAULT 'US' NOT NULL"))
        
        # 2. contacts table
        print("Checking 'contacts' table...")
        await conn.execute(text("ALTER TABLE contacts ADD COLUMN IF NOT EXISTS contact_type VARCHAR(20) DEFAULT 'karin' NOT NULL"))
        await conn.execute(text("ALTER TABLE contacts ADD COLUMN IF NOT EXISTS merchant_id VARCHAR(50)"))
        await conn.execute(text("ALTER TABLE contacts ADD COLUMN IF NOT EXISTS subscriber_id VARCHAR(100)"))
        await conn.execute(text("ALTER TABLE contacts ADD COLUMN IF NOT EXISTS bank_name VARCHAR(255)"))
        await conn.execute(text("ALTER TABLE contacts ADD COLUMN IF NOT EXISTS routing_number VARCHAR(9)"))
        await conn.execute(text("ALTER TABLE contacts ADD COLUMN IF NOT EXISTS account_number VARCHAR(50)"))
        
        # 3. accounts table
        print("Checking 'accounts' table...")
        await conn.execute(text("ALTER TABLE accounts ADD COLUMN IF NOT EXISTS is_main BOOLEAN DEFAULT TRUE NOT NULL"))
        await conn.execute(text("ALTER TABLE accounts ADD COLUMN IF NOT EXISTS parent_account_id INTEGER REFERENCES accounts(id)"))
        await conn.execute(text("ALTER TABLE accounts ADD COLUMN IF NOT EXISTS name VARCHAR(100) DEFAULT 'Main Account' NOT NULL"))
        
        # 4. transactions table
        print("Checking 'transactions' table...")
        await conn.execute(text("ALTER TABLE transactions ADD COLUMN IF NOT EXISTS commentary TEXT"))
        await conn.execute(text("ALTER TABLE transactions ADD COLUMN IF NOT EXISTS subscriber_id VARCHAR(100)"))
        await conn.execute(text("ALTER TABLE transactions ADD COLUMN IF NOT EXISTS payment_request_id INTEGER REFERENCES payment_requests(id)"))
        
        # 5. scheduled_payments table
        print("Checking 'scheduled_payments' table...")
        await conn.execute(text("ALTER TABLE scheduled_payments ADD COLUMN IF NOT EXISTS funding_account_id INTEGER REFERENCES accounts(id)"))
        await conn.execute(text("ALTER TABLE scheduled_payments ADD COLUMN IF NOT EXISTS subscriber_id VARCHAR(100)"))
        
        print("✅ Column checks complete.")

    # 6. Admin User check
    async with SessionLocal() as db:
        admin_email = "admin@example.com"
        admin_password = os.getenv("ADMIN_PASSWORD")
        
        print(f"Checking for admin user: {admin_email}...")
        result = await db.execute(select(User).filter(User.email == admin_email))
        user = result.scalars().first()
        
        if user:
            print(f"User {admin_email} exists. Ensuring role is admin and resetting password.")
            user.role = "admin"
            user.password_hash = pwd_context.hash(admin_password)
        else:
            print(f"Creating new admin user: {admin_email}")
            user = User(
                first_name="Ikarin",
                last_name="Admin",
                email=admin_email,
                password_hash=pwd_context.hash(admin_password),
                role="admin"
            )
            db.add(user)
        
        await db.commit()
        print(f"✅ Admin user ready.")

if __name__ == "__main__":
    asyncio.run(migrate())
