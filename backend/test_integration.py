import asyncio
import httpx
import uuid
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import select
from database import Base, User, Account, ScheduledPayment, Transaction
import os
from datetime import datetime, timedelta

DATABASE_URL = os.getenv("DATABASE_URL")
SIMULATOR_URL = os.getenv("SIMULATOR_URL")
SIMULATOR_API_KEY = os.getenv("SIMULATOR_API_KEY")

async def test_vendor_integration():
    engine = create_async_engine(DATABASE_URL)
    async with engine.connect() as conn:
        # 1. Check if we can reach the simulator
        try:
            async with httpx.AsyncClient() as client:
                res = await client.get(f"{SIMULATOR_URL}/vendors")
                print(f"Simulator vendors: {res.status_code}")
                if res.status_code == 200:
                    vendors = res.json()["vendors"]
                    print(f"Found {len(vendors)} vendors")
        except Exception as e:
            print(f"Error reaching simulator: {e}")
            return

        # 2. Check if main.py changes work (we'll just check if the code runs)
        # We'll simulate a scheduled payment to a vendor
        async with AsyncSession(engine) as session:
            # Find a user to be the sender
            result = await session.execute(select(User).limit(1))
            user = result.scalar_one_or_none()
            if not user:
                print("No user found in DB")
                return
            
            # Find an account
            result = await session.execute(select(Account).where(Account.user_id == user.id))
            account = result.scalar_one_or_none()
            if not account:
                print("No account found for user")
                return

            print(f"Using User: {user.email}, Account: {account.id}")

            # Create a scheduled payment to a vendor (e.g. Austin Energy)
            vendor_email = "billing@austinenergy.com" # From seed.py logic
            
            new_pmt = ScheduledPayment(
                user_id=user.id,
                funding_account_id=account.id,
                recipient_email=vendor_email,
                amount=75.50,
                frequency="Monthly",
                start_date=datetime.utcnow(),
                next_run_at=datetime.utcnow() - timedelta(minutes=1), # Make it due
                status="Active",
                subscriber_id="TEST-SUB-999",
                idempotency_key=str(uuid.uuid4()),
                retry_count=0,
                end_condition="Until Cancelled"
            )
            session.add(new_pmt)
            await session.commit()
            await session.refresh(new_pmt)
            print(f"Created scheduled payment ID: {new_pmt.id} to vendor {vendor_email}")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(test_vendor_integration())
