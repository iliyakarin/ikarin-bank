import asyncio
import os
import sys
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from passlib.context import CryptContext

# Set path to import models and config
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__))))
from models.user import User
from models.account import Account
from config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def seed_data():
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # 1. Create Test User
        user_email = "testuser@karinbank.com"
        res = await session.execute(text("SELECT id FROM users WHERE email = :email"), {"email": user_email})
        user_id = res.scalar()
        
        if not user_id:
            user = User(
                first_name="Test",
                last_name="User",
                email=user_email,
                password_hash=pwd_context.hash("TestPass123!"),
                role="user"
            )
            session.add(user)
            await session.flush()
            user_id = user.id
            print(f"User {user_email} created")
        else:
            print(f"User {user_email} already exists")

        # 2. Create Main Account for User if missing
        res = await session.execute(text("SELECT id FROM accounts WHERE user_id = :uid"), {"uid": user_id})
        acc_id = res.scalar()
        
        if not acc_id:
            account = Account(
                user_id=user_id,
                name="Main Account",
                balance=100000, # $1000.00 in cents
                is_main=True
            )
            session.add(account)
            print(f"Account for {user_email} created")
        
        await session.commit()

        # 3. Create Recipient User
        recipient_email = "recipient@karinbank.com"
        res = await session.execute(text("SELECT id FROM users WHERE email = :email"), {"email": recipient_email})
        recipient_id = res.scalar()
        
        if not recipient_id:
            recipient = User(
                first_name="Recipient",
                last_name="User",
                email=recipient_email,
                password_hash=pwd_context.hash("TestPass123!"),
                role="user"
            )
            session.add(recipient)
            await session.flush()
            recipient_id = recipient.id
            print(f"User {recipient_email} created")
        
        # 4. Create Account for Recipient
        res = await session.execute(text("SELECT id FROM accounts WHERE user_id = :uid"), {"uid": recipient_id})
        if not res.scalar():
            account = Account(
                user_id=recipient_id,
                name="Main Account",
                balance=0,
                is_main=True
            )
            session.add(account)
            print(f"Account for {recipient_email} created")

        await session.commit()
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(seed_data())
