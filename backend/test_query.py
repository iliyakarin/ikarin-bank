import asyncio
from sqlalchemy import select
from database import SessionLocal, ScheduledPayment
from datetime import datetime

async def test_query():
    try:
        async with SessionLocal() as db:
            now = datetime.utcnow()
            print("Executing query...")
            stmt = select(ScheduledPayment).where(
                ScheduledPayment.status.in_(["Active", "Retrying"])
            )
            print(f"Statement: {stmt}")
            result = await db.execute(stmt)
            payments = result.scalars().all()
            print(f"Result found: {len(payments)} payments")
            for p in payments:
                print(f"ID: {p.id}, Recipient: {p.recipient_email}, Status: {p.status}")
    except Exception as e:
        print(f"Query error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_query())
