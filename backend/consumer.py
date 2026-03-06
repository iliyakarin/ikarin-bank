import json
import os
import time
import asyncio
from datetime import datetime
from typing import List, Dict, Any

import logging
import clickhouse_connect
from confluent_kafka import Consumer, KafkaError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration from .env
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC")
KAFKA_ACTIVITY_TOPIC = os.getenv("KAFKA_ACTIVITY_TOPIC")
KAFKA_USER = os.getenv("KAFKA_USER")
KAFKA_PASSWORD = os.getenv("KAFKA_PASSWORD", "")
CH_HOST = os.getenv("CLICKHOUSE_HOST")
CH_PORT = int(os.getenv("CLICKHOUSE_PORT", 8123))
CH_USER = os.getenv("CLICKHOUSE_USER")
CH_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD", "")

# OPTIMIZED CONFIGURATION
OPTIMAL_BATCH_SIZE = 1000
OPTIMAL_FLUSH_INTERVAL = 30
OPTIMAL_SESSION_TIMEOUT = 10000
MAX_RETRIES = 3

# ClickHouse client (connection pool ready for async operations)
ch_client = None


def get_clickhouse_client():
    """Get or create ClickHouse client with connection pooling"""
    global ch_client
    if ch_client is None:
        ch_client = clickhouse_connect.get_client(
            host=CH_HOST,
            port=CH_PORT,
            username=CH_USER,
            password=CH_PASSWORD
        )
        logger.info("🚀 ClickHouse client connected with performance optimizations")
    return ch_client


def log_malformed_message_batch(malformed_messages):
    """Batch log malformed messages to reduce I/O overhead"""
    if not malformed_messages:
        return

    dlq_file = "/tmp/kafka_dlq.jsonl"
    timestamp = datetime.now().isoformat()

    # Batch write for better performance
    batch_entries = [
        json.dumps(
            {
                "timestamp": timestamp,
                "partition": msg["partition"],
                "offset": msg["offset"],
                "error": msg["error"],
                "raw_message": msg["raw_message"],
            }
        )
        for msg in malformed_messages
    ]

    try:
        with open(dlq_file, "a") as f:
            f.write("\n".join(batch_entries) + "\n")
        logger.info(
            f"📝 Batch logged {len(malformed_messages)} malformed messages to DLQ"
        )
    except Exception as e:
        logger.error(f"❌ Failed to write to DLQ: {e}")


async def flush_to_clickhouse_async(batch: List[Dict[str, Any]]) -> bool:
    """Asynchronous ClickHouse insertion for better performance"""
    if not batch:
        return True

    try:
        start_time = time.time()
        client = get_clickhouse_client()

        # Prepare data for bulk insert (ClickHouse optimized format)
        data_to_insert = [
            [
                msg["transaction_id"],
                msg.get("parent_id") or "00000000-0000-0000-0000-000000000000",
                msg["account_id"],
                msg.get("sender_email") or "",
                msg.get("recipient_email") or "",
                msg["amount"],
                msg["category"],
                msg["merchant"],
                msg.get("transaction_type") or "expense",
                msg.get("transaction_side") or "",
                msg["timestamp"],
            ]
            for msg in batch
        ]

        # Use async insert if available, otherwise fallback to sync
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: client.insert(
                    "banking.transactions",
                    data_to_insert,
                    column_names=[
                        "transaction_id",
                        "parent_id",
                        "account_id",
                        "sender_email",
                        "recipient_email",
                        "amount",
                        "category",
                        "merchant",
                        "transaction_type",
                        "transaction_side",
                        "event_time",
                    ],
                ),
            )
            logger.info(f"🚀 Async flush completed in {time.time() - start_time:.2f}s")
            return True
        except Exception as e:
            logger.warning(f"⚠️ Async flush failed, falling back to sync: {e}")
            # Fallback to sync insert
            client.insert(
                "banking.transactions",
                data_to_insert,
                column_names=[
                    "transaction_id",
                    "parent_id",
                    "account_id",
                    "sender_email",
                    "recipient_email",
                    "amount",
                    "category",
                    "merchant",
                    "transaction_type",
                    "transaction_side",
                    "event_time",
                ],
            )
            logger.info(f"📝 Sync flush completed in {time.time() - start_time:.2f}s")
            return True

    except Exception as e:
        logger.error(f"❌ ClickHouse flush failed: {e}")
        return False


async def flush_activity_to_clickhouse(batch: List[Dict[str, Any]]) -> bool:
    """Flush activity events to ClickHouse banking_log.activity_events"""
    if not batch:
        return True

    try:
        start_time = time.time()
        client = get_clickhouse_client()

        data_to_insert = [
            [
                msg["event_id"],
                msg["user_id"],
                msg["category"],
                msg["action"],
                msg["event_time"],
                msg["title"],
                msg.get("details", "{}"),
            ]
            for msg in batch
        ]

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: client.insert(
                    "banking.activity_events",
                    data_to_insert,
                    column_names=[
                        "event_id",
                        "user_id",
                        "category",
                        "action",
                        "event_time",
                        "title",
                        "details",
                    ],
                ),
            )
            logger.info(f"📋 Activity flush completed in {time.time() - start_time:.2f}s ({len(batch)} events)")
            return True
        except Exception as e:
            logger.warning(f"⚠️ Async activity flush failed, sync fallback: {e}")
            client.insert(
                "banking.activity_events",
                data_to_insert,
                column_names=[
                    "event_id",
                    "user_id",
                    "category",
                    "action",
                    "event_time",
                    "title",
                    "details",
                ],
            )
            return True
    except Exception as e:
        logger.error(f"❌ Activity ClickHouse flush failed: {e}")
        return False


async def run_consumer():
    """Optimized Kafka consumer with better batching and async processing"""
    logger.info("🚀 Starting optimized Kafka consumer...")

    # OPTIMIZED Kafka Consumer Config
    conf = {
        "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
        "group.id": "clickhouse-bi-group",
        "auto.offset.reset": "latest",  # Start from latest, not beginning!
        "enable.auto.commit": False,  # Manual commit control
        "session.timeout.ms": OPTIMAL_SESSION_TIMEOUT,
        "metadata.max.age.ms": 600000,  # 10 minutes instead of 30 seconds
        "socket.keepalive.enable": True,

        "fetch.min.bytes": 1,
        "fetch.error.backoff.ms": 1000,
        "retry.backoff.ms": 1000,
    }

    if KAFKA_USER and KAFKA_PASSWORD:
        conf.update(
            {
                "sasl.mechanisms": "PLAIN",
                "security.protocol": "SASL_PLAINTEXT",
                "sasl.username": KAFKA_USER,
                "sasl.password": KAFKA_PASSWORD,
            }
        )

    consumer = Consumer(conf)
    consumer.subscribe([KAFKA_TOPIC, KAFKA_ACTIVITY_TOPIC])

    buffer = []
    activity_buffer = []
    last_flush_time = time.time()
    processed_count = 0
    malformed_batch = []

    logger.info(
        f"✅ Consumer configured with batch_size={OPTIMAL_BATCH_SIZE}, flush_interval={OPTIMAL_FLUSH_INTERVAL}"
    )

    try:
        while True:
            # Poll must be synchronous because confluent_kafka.Consumer is not async
            # We run it in a loop but yield to other tasks if we were doing other async work
            # Since this is a dedicated consumer loop, blocking here is generally fine,
            # but we can sleep slightly if we want to be nice to the event loop.
            msg = consumer.poll(1.0)  # 1 second poll

            if msg is None:
                # Still check flush interval even if no messages
                if (buffer or activity_buffer) and (time.time() - last_flush_time >= OPTIMAL_FLUSH_INTERVAL):
                     if buffer:
                         logger.info(f"⏱️ Time-based flush of {len(buffer)} transaction messages...")
                         if await flush_to_clickhouse_async(buffer):
                            buffer = []
                     if activity_buffer:
                         logger.info(f"⏱️ Time-based flush of {len(activity_buffer)} activity events...")
                         if await flush_activity_to_clickhouse(activity_buffer):
                            activity_buffer = []
                     consumer.commit()
                     last_flush_time = time.time()
                await asyncio.sleep(0.01) # Yield to event loop
                continue

            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    logger.info("🏁 Reached end of partition")
                    continue
                else:
                    logger.error(f"❌ Kafka error: {msg.error()}")
                    continue

            try:
                # Fast JSON parsing with error handling
                try:
                    val = json.loads(msg.value().decode("utf-8"))
                except json.JSONDecodeError as e:
                    logger.warning(f"⚠️  Malformed JSON: {e}")
                    malformed_batch.append(
                        {
                            "partition": msg.partition(),
                            "offset": msg.offset(),
                            "error": f"JSONDecodeError: {e}",
                            "raw_message": msg.value().decode(
                                "utf-8", errors="replace"
                            ),
                        }
                    )
                    consumer.commit()  # Commit offset even for malformed messages
                    continue

                # Validate required fields
                # Note: 'timestamp' might be 'event_time' or similar depending on producer.
                # The original consumer used 'timestamp'.
                # Let's be flexible or ensure it matches.
                # Original consumer expected: transaction_id, account_id, amount, category, merchant, timestamp
                required_fields = [
                    "transaction_id",
                    "account_id",
                    "amount",
                    "category",
                    "merchant",
                    "timestamp",
                ]
                missing_fields = [f for f in required_fields if f not in val]

                if missing_fields:
                    logger.warning(f"⚠️  Missing fields: {missing_fields}")
                    malformed_batch.append(
                        {
                            "partition": msg.partition(),
                            "offset": msg.offset(),
                            "error": f"MissingFields: {missing_fields}",
                            "raw_message": val,
                        }
                    )
                    consumer.commit()
                    continue

                # Add to buffer with minimal processing
                # Route based on topic
                msg_topic = msg.topic()
                if msg_topic == KAFKA_ACTIVITY_TOPIC:
                    activity_buffer.append(val)
                else:
                    buffer.append(val)
                processed_count += 1

                # Flush conditions
                should_flush = (
                    len(buffer) + len(activity_buffer) >= OPTIMAL_BATCH_SIZE
                    or time.time() - last_flush_time >= OPTIMAL_FLUSH_INTERVAL
                )

                if should_flush:
                    logger.info(
                        f"📊 Flushing {len(buffer)} tx + {len(activity_buffer)} activity (total processed: {processed_count})"
                    )

                    # Process malformed messages first
                    if malformed_batch:
                        log_malformed_message_batch(malformed_batch)
                        malformed_batch = []

                    # Flush valid messages
                    tx_success = await flush_to_clickhouse_async(buffer) if buffer else True
                    act_success = await flush_activity_to_clickhouse(activity_buffer) if activity_buffer else True

                    if tx_success and act_success:
                        consumer.commit()
                        buffer = []
                        activity_buffer = []
                        last_flush_time = time.time()

                        if processed_count % 1000 == 0:
                            logger.info(
                                f"🎉 Processed {processed_count} messages so far!"
                            )

            except Exception as e:
                logger.error(f"❌ Message processing error: {e}")
                consumer.commit()  # Still commit to avoid reprocessing
                continue

    except KeyboardInterrupt:
        logger.info("🛑 Consumer stopped by user")
    except Exception as e:
        logger.error(f"❌ Consumer error: {e}")
    finally:
        # Final flush
        if buffer:
            logger.info(f"🏁 Final flush of {len(buffer)} messages")
            await flush_to_clickhouse_async(buffer)

        if activity_buffer:
            logger.info(f"🏁 Final flush of {len(activity_buffer)} activity events")
            await flush_activity_to_clickhouse(activity_buffer)

        if malformed_batch:
            log_malformed_message_batch(malformed_batch)

        consumer.close()
        logger.info("✅ Consumer stopped")


if __name__ == "__main__":
    asyncio.run(run_consumer())
