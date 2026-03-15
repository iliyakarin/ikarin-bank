import json
import os
import time
import asyncio
import datetime
from datetime import timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import SessionLocal, Outbox, Transaction
from aiokafka import AIOKafkaProducer

from config import settings

async def process_outbox():
    print("🚀 Outbox worker started...")
    
    producer = AIOKafkaProducer(
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        enable_idempotence=True,
        security_protocol="SASL_PLAINTEXT",
        sasl_mechanism="PLAIN",
        sasl_plain_username=settings.KAFKA_USER,
        sasl_plain_password=settings.KAFKA_PASSWORD,
    )
    
    max_retries = 30
    retry_count = 0
    while retry_count < max_retries:
        try:
            await producer.start()
            print("🚀 Kafka Producer started successfully")
            break
        except Exception as e:
            retry_count += 1
            print(f"⏳ Waiting for Kafka... ({retry_count}/{max_retries}) Error: {e}")
            await asyncio.sleep(2)
    else:
        print("❌ Failed to start Kafka Producer after multiple retries")
        return
    
    try:
        while True:
            async with SessionLocal() as db:
                try:
                    # Fetch unprocessed events
                    result = await db.execute(select(Outbox).filter(Outbox.status == "pending").limit(50))
                    events = result.scalars().all()
                    
                    for event in events:
                        try:
                            payload_data = event.payload
                            tx_id = payload_data.get("transaction_id")
                            
                            # Route to the correct topic based on event type
                            if event.event_type == "activity_event":
                                target_topic = settings.KAFKA_ACTIVITY_TOPIC
                            else:
                                target_topic = settings.KAFKA_TOPIC
                            
                            # Send to Kafka
                            await producer.send_and_wait(
                                target_topic, 
                                json.dumps(payload_data).encode("utf-8")
                            )

                            
                            # Update outbox status
                            event.status = "processed"
                            event.processed_at = datetime.datetime.now(datetime.timezone.utc)
                            
                            # Update transaction status in Postgres
                            if tx_id:
                                result = await db.execute(select(Transaction).filter(Transaction.id == tx_id))
                                tx = result.scalars().first()
                                if tx:
                                    tx.status = "sent_to_kafka"
                            
                            await db.commit()
                            print(f"✅ Processed event {event.id} for transaction {tx_id}")
                            
                        except Exception as e:
                            print(f"❌ Failed to process event {event.id}: {e}")
                            # db.rollback() is fully implicit with context managers in async mode per session, but for
                            # specific event loops it's safer to just let the iteration handle faults
                            event.status = "failed"
                            await db.commit()
                    
                    if not events:
                        await asyncio.sleep(1) # Wait for new events
                except Exception as loop_e:
                    print(f"Loop processing error: {loop_e}")
                
    except Exception as e:
        print(f"💥 Outbox worker fatal error: {e}")
    finally:
        await producer.stop()

if __name__ == "__main__":
    asyncio.run(process_outbox())
