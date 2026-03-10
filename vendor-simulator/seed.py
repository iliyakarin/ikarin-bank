import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from models import Base, Merchant

DATABASE_URL = os.getenv("DATABASE_URL")

MERCHANTS = [
    {"name": "Austin Energy", "merchant_id": "austin-energy-001", "category": "Utilities"},
    {"name": "PG&E", "merchant_id": "pge-001", "category": "Utilities"},
    {"name": "Duke Energy", "merchant_id": "duke-energy-001", "category": "Utilities"},
    {"name": "Waste Management", "merchant_id": "waste-mgmt-001", "category": "Utilities"},
    {"name": "AT&T", "merchant_id": "att-001", "category": "Telecom"},
    {"name": "Verizon", "merchant_id": "verizon-001", "category": "Telecom"},
    {"name": "T-Mobile", "merchant_id": "tmobile-001", "category": "Telecom"},
    {"name": "Comcast", "merchant_id": "comcast-001", "category": "Telecom"},
    {"name": "Amazon (Store Card)", "merchant_id": "amazon-card-001", "category": "Retail"},
    {"name": "Amex", "merchant_id": "amex-001", "category": "Finance"},
    {"name": "Discover", "merchant_id": "discover-001", "category": "Finance"},
    {"name": "Chase Credit", "merchant_id": "chase-credit-001", "category": "Finance"},
    {"name": "State Farm", "merchant_id": "state-farm-001", "category": "Services"},
    {"name": "Geico", "merchant_id": "geico-001", "category": "Services"},
    {"name": "Netflix", "merchant_id": "netflix-001", "category": "Services"},
]

async def seed():
    engine = create_async_engine(DATABASE_URL)
    AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        # Seed Merchants
        for merchant_data in MERCHANTS:
            merchant = Merchant(**merchant_data)
            session.add(merchant)
        
        try:
            await session.commit()
            print("Vendor Simulator database seeded successfully!")
        except Exception as e:
            await session.rollback()
            print(f"Error seeding database: {e}")
        finally:
            await session.close()
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(seed())
