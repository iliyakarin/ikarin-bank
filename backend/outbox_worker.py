"""Outbox processor - consumes pending events from Postgres and sends to Kafka."""
import asyncio
import logging
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy import select

from config import settings
from database import SessionLocal
from models.management import Outbox
from outbox_service import ProducerManager, send_to_kafka

logger = logging.getLogger(__name__)

async def process_outbox():
    """Main loop for the outbox worker."""
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    while True:
        try:
            async with AsyncSession(engine) as session:
                result = await session.execute(
                    select(Outbox).where(Outbox.status == "pending").limit(50)
                )
                events = result.scalars().all()

                if not events:
                    await asyncio.sleep(1)
                    continue

                for event in events:
                    try:
                        success = await send_to_kafka(session, event)
                        if success:
                            logger.info(f"✅ Event {event.id} processed.")
                        else:
                            logger.error(f"❌ Event {event.id} failed.")
                    except Exception as e:
                        logger.error(f"❌ error: {e}")
                        continue

                await session.commit()
        except Exception as e:
            logger.error(f"Loop error: {e}")
            await asyncio.sleep(2)

async def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    logger.info("🚀 Starting Outbox Worker...")
    try:
        await process_outbox()
    except asyncio.CancelledError:
        logger.info("Shutting down...")

if __name__ == "__main__":
    asyncio.run(main())
