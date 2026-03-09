import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from models import Base, Bank

DATABASE_URL = os.getenv("DATABASE_URL")

BANKS = [
    {"name": "JPMorgan Chase", "routing_number": "021000021"},
    {"name": "Bank of America", "routing_number": "026009593"},
    {"name": "Wells Fargo", "routing_number": "121000248"},
    {"name": "Citibank", "routing_number": "021000089"},
    {"name": "Capital One", "routing_number": "051405515"},
]

async def seed():
    engine = create_async_engine(DATABASE_URL)
    AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        # Seed Banks
        for bank_data in BANKS:
            bank = Bank(**bank_data)
            session.add(bank)
        
        try:
            await session.commit()
            print("Mock Fed Gateway database seeded successfully!")
        except Exception as e:
            await session.rollback()
            print(f"Error seeding database: {e}")
        finally:
            await session.close()
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(seed())
