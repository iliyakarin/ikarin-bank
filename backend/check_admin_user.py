
import asyncio
from database import SessionLocal
from models.user import User
from sqlalchemy import select

async def check_user():
    async with SessionLocal() as db:
        query = select(User).where(User.email == "ikarin@admin.com")
        result = await db.execute(query)
        user = result.scalar_one_or_none()
        
        if user:
            print(f"User ID: {user.id}")
            print(f"Email: {user.email}")
            print(f"Role: {user.role}")
            print(f"Is Active: {user.is_active}")
        else:
            print("User ikarin@admin.com not found")

if __name__ == "__main__":
    asyncio.run(check_user())
