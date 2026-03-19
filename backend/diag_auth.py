import asyncio
import os
from sqlalchemy import select
from passlib.context import CryptContext
from database import User, SessionLocal
from auth_utils import verify_password as verify_auth, pwd_context as auth_pwd_context
from migrations import pwd_context as migration_pwd_context

async def diag():
    print(f"ADMIN_EMAIL: {os.getenv('ADMIN_EMAIL')}")
    print(f"ADMIN_PASSWORD: {os.getenv('ADMIN_PASSWORD')}")

    async with SessionLocal() as db:
        result = await db.execute(select(User).filter(User.email == os.getenv('ADMIN_EMAIL')))
        user = result.scalars().first()

        if not user:
            print("❌ Admin user not found in DB")
            return

        print(f"✅ Found user: {user.email}")
        print(f"Stored Role: {user.role}")
        print(f"Stored Hash: {user.password_hash}")

        password = os.getenv('ADMIN_PASSWORD')

        v_auth = auth_pwd_context.verify(password, user.password_hash)
        v_mig = migration_pwd_context.verify(password, user.password_hash)

        print(f"Verification (auth_utils context): {v_auth}")
        print(f"Verification (migration context): {v_mig}")

        # Test hashing a new one
        new_hash = auth_pwd_context.hash(password)
        print(f"New Hash generated: {new_hash}")
        v_new = auth_pwd_context.verify(password, new_hash)
        print(f"Verification of NEW hash: {v_new}")

if __name__ == "__main__":
    asyncio.run(diag())
