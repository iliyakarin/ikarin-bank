import json
import time
import asyncio
import logging
from typing import List, Dict, Any

from confluent_kafka import Consumer, KafkaError
from config import settings
from security_utils import decrypt_payload
from handlers.message_handlers import (
    flush_batch_to_clickhouse,
    prepare_transaction_data,
    prepare_activity_data,
    TRANSACTION_COLUMNS,
    ACTIVITY_COLUMNS
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# OPTIMIZED CONFIGURATION
OPTIMAL_BATCH_SIZE = 100
OPTIMAL_FLUSH_INTERVAL = 5
OPTIMAL_SESSION_TIMEOUT = 10000

class KafkaConsumerApp:
    def __init__(self):
        self.conf = self._get_kafka_config()
        self.consumer = Consumer(self.conf)
        self.topic_tx = settings.KAFKA_TOPIC
        self.topic_activity = settings.KAFKA_ACTIVITY_TOPIC
        
        self.tx_buffer = []
        self.activity_buffer = []
        self.malformed_batch = []
        self.last_flush_time = time.time()
        self.processed_count = 0

    def _get_kafka_config(self) -> dict:
        conf = {
            "bootstrap.servers": settings.KAFKA_BOOTSTRAP_SERVERS,
            "group.id": "clickhouse-bi-group-v4",
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
            "session.timeout.ms": OPTIMAL_SESSION_TIMEOUT,
            "socket.keepalive.enable": True,
        }
        if settings.KAFKA_USER and settings.KAFKA_PASSWORD:
            conf.update({
                "sasl.mechanisms": "PLAIN",
                "security.protocol": "SASL_PLAINTEXT",
                "sasl.username": settings.KAFKA_USER,
                "sasl.password": settings.KAFKA_PASSWORD,
            })
        return conf

    async def flush_all(self):
        """Flush all buffers to ClickHouse."""
        if not self.tx_buffer and not self.activity_buffer:
            return

        logger.info(f"📊 Flushing {len(self.tx_buffer)} tx + {len(self.activity_buffer)} activity")
        
        tasks = []
        if self.tx_buffer:
            data = prepare_transaction_data(self.tx_buffer)
            tasks.append(flush_batch_to_clickhouse("transactions", TRANSACTION_COLUMNS, data))
            
        if self.activity_buffer:
            data = prepare_activity_data(self.activity_buffer)
            tasks.append(flush_batch_to_clickhouse("activity_events", ACTIVITY_COLUMNS, data))

        if self.malformed_batch:
            self._log_malformed_batch()
            self.malformed_batch = []

        results = await asyncio.gather(*tasks)
        if all(results):
            self.consumer.commit()
            self.tx_buffer = []
            self.activity_buffer = []
            self.last_flush_time = time.time()

    def _log_malformed_batch(self):
        dlq_file = "/tmp/kafka_dlq.jsonl"
        try:
            with open(dlq_file, "a") as f:
                for msg in self.malformed_batch:
                    f.write(json.dumps(msg) + "\n")
            logger.info(f"📝 Logged {len(self.malformed_batch)} malformed messages to DLQ")
        except OSError as e:
            logger.error(f"❌ Failed to write to DLQ: {e}")

    def _validate_message(self, topic: str, val: dict) -> List[str]:
        if topic == self.topic_activity:
            required = ["event_id", "user_id", "category", "action", "event_time", "title"]
        else:
            required = ["transaction_id", "account_id", "amount", "category", "merchant", "timestamp"]
        return [f for f in required if f not in val]

    async def run(self):
        logger.info(f"🚀 Starting refactored Kafka consumer (batch={OPTIMAL_BATCH_SIZE})")
        self.consumer.subscribe([self.topic_tx, self.topic_activity])
        
        try:
            while True:
                msg = self.consumer.poll(1.0)
                
                if msg is None:
                    if (time.time() - self.last_flush_time) >= OPTIMAL_FLUSH_INTERVAL:
                        await self.flush_all()
                    await asyncio.sleep(0.01)
                    continue

                if msg.error():
                    if msg.error().code() != KafkaError._PARTITION_EOF:
                        logger.error(f"❌ Kafka error: {msg.error()}")
                    continue

                try:
                    raw_val = msg.value().decode("utf-8")
                    val = json.loads(raw_val)
                    
                    topic = msg.topic()
                    val = decrypt_payload(val, settings.KAFKA_MESSAGE_ENCRYPTION_KEY)
                    
                    missing = self._validate_message(topic, val)
                    if missing:
                        logger.warning(f"⚠️ Missing fields in {topic}: {missing}")
                        self.malformed_batch.append({
                            "partition": msg.partition(), "offset": msg.offset(),
                            "error": f"MissingFields: {missing}", "raw_message": val
                        })
                        self.consumer.commit()
                        continue

                    if topic == self.topic_activity:
                        self.activity_buffer.append(val)
                    else:
                        self.tx_buffer.append(val)
                        
                    self.processed_count += 1
                    
                    if (len(self.tx_buffer) + len(self.activity_buffer)) >= OPTIMAL_BATCH_SIZE:
                        await self.flush_all()

                except Exception as e:
                    logger.error(f"❌ Processing error: {e}")
                    self.consumer.commit()

        except KeyboardInterrupt:
            logger.info("🛑 Stopped by user")
        finally:
            await self.flush_all()
            self.consumer.close()
            logger.info("✅ Shutdown complete")

if __name__ == "__main__":
    app = KafkaConsumerApp()
    asyncio.run(app.run())
