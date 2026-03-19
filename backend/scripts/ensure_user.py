import asyncio
import os
from sqlalchemy import select
from passlib.context import CryptContext
from database import User, Account, SessionLocal

# Load from environment
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "REDACTED" # Default dev password

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def ensure_user_exists():
    async with SessionLocal() as db:
        # Check if user already exists
        result = await db.execute(select(User).filter(User.email == ADMIN_EMAIL))
        user = result.scalars().first()

        if not user:
            print(f"Creating new test user: {ADMIN_EMAIL}")
            user = User(
                first_name="Test",
                last_name="User",
                email=ADMIN_EMAIL,
                password_hash=pwd_context.hash(ADMIN_PASSWORD),
                role="admin"
            )
            db.add(user)
            await db.flush() # Get user ID

            # Create main account
            account = Account(
                user_id=user.id,
                name="Main Account",
                is_main=True,
                balance=0.00
            )
            db.add(account)
            print(f"User {ADMIN_EMAIL} and main account created.")
        else:
            print(f"User {ADMIN_EMAIL} already exists.")
            # Ensure they have an account
            acc_result = await db.execute(select(Account).filter(Account.user_id == user.id, Account.is_main == True))
            if not acc_result.scalars().first():
                account = Account(
                    user_id=user.id,
                    name="Main Account",
                    is_main=True,
                    balance=0.00
                )
                db.add(account)
                print(f"Main account created for existing user {ADMIN_EMAIL}.")

        await db.commit()

if __name__ == "__main__":
    asyncio.run(ensure_user_exists())
