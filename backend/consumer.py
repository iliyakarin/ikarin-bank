import json
import os
import time
from datetime import datetime
from typing import List, Dict, Any
from confluent_kafka import Consumer, KafkaException, TopicPartition, KafkaError
import logging
import clickhouse_connect

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration from .env
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC")
KAFKA_USER = os.getenv("KAFKA_USER")
KAFKA_PASSWORD = os.getenv("KAFKA_PASSWORD", "")
CH_HOST = os.getenv("CLICKHOUSE_HOST")
CH_PORT = int(os.getenv("CLICKHOUSE_PORT", 8123))
CH_USER = os.getenv("CLICKHOUSE_USER")
CH_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD", "")

OPTIMAL_BATCH_SIZE = 1000
OPTIMAL_FLUSH_INTERVAL = 30

ch_client = None

def get_clickhouse_client():
    global ch_client
    if ch_client is None:
        ch_client = clickhouse_connect.get_client(
            host=CH_HOST,
            port=CH_PORT,
            username=CH_USER,
            password=CH_PASSWORD,
        )
        logger.info("🚀 ClickHouse client connected (Synchronous)")
    return ch_client

def flush_to_clickhouse(batch: List[Dict[str, Any]]) -> bool:
    if not batch:
        return True
    try:
        start_time = time.time()
        client = get_clickhouse_client()
        data_to_insert = []
        for msg in batch:
            row = [
                msg["transaction_id"],
                msg.get("parent_id") or "00000000-0000-0000-0000-000000000000",
                msg["account_id"],
                msg.get("sender_email", ""),
                msg.get("recipient_email", ""),
                msg["amount"],
                msg["category"],
                msg["merchant"],
                msg.get("transaction_type", "expense"),
                msg.get("transaction_side", ""),
                msg["timestamp"],
            ]
            data_to_insert.append(row)





        
        client.insert(
            "banking.transactions",
            data_to_insert,
            column_names=[
                "transaction_id", "parent_id", "account_id", "sender_email", 
                "recipient_email", "amount", "category", "merchant", 
                "transaction_type", "transaction_side", "event_time"
            ],
        )
        logger.info(f"✅ Flush completed for {len(batch)} rows in {time.time() - start_time:.2f}s")
        return True
    except Exception as e:
        logger.error(f"❌ ClickHouse flush failed: {e}")
        return False

def run_consumer():
    logger.info("🚀 Starting synchronous Kafka consumer...")
    conf = {
        "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
        "group.id": "clickhouse-pristine-v1",
        "auto.offset.reset": "latest", # We truncated CH, so let's just start from NOW or from latest. 
        # Actually earliest is fine if we want to catch the last few Outbox entries that are clean.


        "enable.auto.commit": False,
        "session.timeout.ms": 6000,
    }

    if KAFKA_USER and KAFKA_PASSWORD:
        conf.update({
            "sasl.mechanisms": "PLAIN",
            "security.protocol": "SASL_PLAINTEXT",
            "sasl.username": KAFKA_USER,
            "sasl.password": KAFKA_PASSWORD,
        })

    consumer = Consumer(conf)
    consumer.subscribe([KAFKA_TOPIC])

    buffer = []
    last_flush_time = time.time()

    try:
        while True:
            msg = consumer.poll(1.0)
            if msg is None:
                # Periodic flush check
                if buffer and (time.time() - last_flush_time >= OPTIMAL_FLUSH_INTERVAL):
                    if flush_to_clickhouse(buffer):
                        consumer.commit()
                        buffer = []
                        last_flush_time = time.time()
                continue

            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                else:
                    logger.error(f"❌ Kafka error: {msg.error()}")
                    continue

            try:
                msg_val = msg.value().decode("utf-8")
                # logger.debug(f"📥 Received: {msg_val}")
                val = json.loads(msg_val)
                buffer.append(val)
                
                if len(buffer) >= OPTIMAL_BATCH_SIZE or (time.time() - last_flush_time >= OPTIMAL_FLUSH_INTERVAL):
                    logger.info(f"📊 Manually flushing {len(buffer)} messages...")
                    if flush_to_clickhouse(buffer):
                        consumer.commit()
                        buffer = []
                        last_flush_time = time.time()
            except Exception as e:
                logger.error(f"❌ Message processing error: {e}")
                consumer.commit()


    except KeyboardInterrupt:
        logger.info("🛑 Stopped by user")
    finally:
        if buffer:
            flush_to_clickhouse(buffer)
        consumer.close()

if __name__ == "__main__":
    run_consumer()
