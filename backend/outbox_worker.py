import json
import os
import time
import asyncio
import datetime
from sqlalchemy.orm import Session
from database import SessionLocal, Outbox, Transaction
from aiokafka import AIOKafkaProducer

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "bank_transactions")
KAFKA_ACTIVITY_TOPIC = os.getenv("KAFKA_ACTIVITY_TOPIC", "bank_activity_events")
KAFKA_USER = os.getenv("KAFKA_USER", "admin")
KAFKA_PASSWORD = os.getenv("KAFKA_PASSWORD", "")

async def process_outbox():
    print("🚀 Outbox worker started...")
    
    producer = AIOKafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        enable_idempotence=True,
        security_protocol="SASL_PLAINTEXT",
        sasl_mechanism="PLAIN",
        sasl_plain_username=KAFKA_USER,
        sasl_plain_password=KAFKA_PASSWORD,
    )
    
    await producer.start()
    
    try:
        while True:
            db: Session = SessionLocal()
            try:
                # Fetch unprocessed events
                events = db.query(Outbox).filter(Outbox.status == "pending").limit(50).all()
                
                for event in events:
                    try:
                        payload_data = event.payload
                        tx_id = payload_data.get("transaction_id")
                        
                        # Route to the correct topic based on event type
                        if event.event_type == "activity_event":
                            target_topic = "bank_activity_events"
                        else:
                            target_topic = KAFKA_TOPIC
                        
                        # Send to Kafka
                        await producer.send_and_wait(
                            target_topic, 
                            json.dumps(payload_data).encode("utf-8")
                        )

                        
                        # Update outbox status
                        event.status = "processed"
                        event.processed_at = datetime.datetime.utcnow()
                        
                        # Update transaction status in Postgres
                        if tx_id:
                            tx = db.query(Transaction).filter(Transaction.id == tx_id).first()
                            if tx:
                                tx.status = "sent_to_kafka"
                        
                        db.commit()
                        print(f"✅ Processed event {event.id} for transaction {tx_id}")
                        
                    except Exception as e:
                        print(f"❌ Failed to process event {event.id}: {e}")
                        db.rollback()
                        # Mark as failed after some retries? For now just skip
                        event.status = "failed"
                        db.commit()
                
                if not events:
                    await asyncio.sleep(1) # Wait for new events
            finally:
                db.close()
                
    except Exception as e:
        print(f"💥 Outbox worker fatal error: {e}")
    finally:
        await producer.stop()

if __name__ == "__main__":
    asyncio.run(process_outbox())
