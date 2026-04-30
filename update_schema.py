import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from backend.config import settings

async def main():
    engine = create_async_engine(settings.DATABASE_URL)
    tables = ['users', 'subscriptions', 'contacts', 'scheduled_payments', 'outbox', 'accounts', 'payment_methods', 'transactions', 'payment_requests', 'idempotency_keys']
    async with engine.begin() as conn:
        for table in tables:
            try:
                await conn.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();")
                await conn.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();")
                print(f"Added columns to {table}")
            except Exception as e:
                print(f"Error on {table}: {e}")

asyncio.run(main())
