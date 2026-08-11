"""Outbox processor - consumes pending events from Postgres and sends to Kafka."""
import asyncio
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pathlib import Path

from database import SessionLocal, engine
from models.management import Outbox
from outbox_service import ProducerManager, send_to_kafka

logger = logging.getLogger(__name__)

async def process_outbox():
    """Main loop for the outbox worker."""
    attempt = 0
    while True:
        Path("/tmp/heartbeat.txt").touch(exist_ok=True)
        try:
            async with SessionLocal() as session:
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
                attempt = 0
        except Exception as e:
            logger.error(f"Loop error: {e}")
            backoff = min(2 ** attempt, 30)
            await asyncio.sleep(backoff)
            attempt += 1

async def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    logger.info("🚀 Starting Outbox Worker...")
    try:
        await process_outbox()
    except asyncio.CancelledError:
        logger.info("Shutting down...")

if __name__ == "__main__":
    asyncio.run(main())
