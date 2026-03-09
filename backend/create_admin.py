import asyncio
import os
from sqlalchemy import select
from passlib.context import CryptContext
from database import User, SessionLocal

# Load from environment
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@karinbank.com")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def create_admin():
    async with SessionLocal() as db:
        # Check if user already exists
        result = await db.execute(select(User).filter(User.email == ADMIN_EMAIL))
        user = result.scalars().first()
        
        if user:
            print(f"User {ADMIN_EMAIL} already exists. Updating role and password.")
            user.role = "admin"
            user.password_hash = pwd_context.hash(ADMIN_PASSWORD)
        else:
            print(f"Creating new admin user: {ADMIN_EMAIL}")
            user = User(
                first_name="Admin",
                last_name="User",
                email=ADMIN_EMAIL,
                password_hash=pwd_context.hash(ADMIN_PASSWORD),
                role="admin"
            )
            db.add(user)
        
        await db.commit()
        print(f"Admin user ready: {ADMIN_EMAIL} / {'*' * len(ADMIN_PASSWORD)}")

if __name__ == "__main__":
    asyncio.run(create_admin())
