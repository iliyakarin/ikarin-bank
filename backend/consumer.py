import json
import os
import time
import clickhouse_connect
from confluent_kafka import Consumer, KafkaError

# Configuration from .env
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
CH_HOST = os.getenv("CLICKHOUSE_HOST", "clickhouse")
CH_PORT = int(os.getenv("CLICKHOUSE_PORT", 8123))

# ClickHouse Client
ch_client = clickhouse_connect.get_client(host=CH_HOST, port=CH_PORT)

# Kafka Consumer Config
conf = {
    'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
    'group.id': 'clickhouse-bi-group',
    'auto.offset.reset': 'earliest',
    'enable.auto.commit': False  # We will commit manually for Exactly-Once
}

consumer = Consumer(conf)
consumer.subscribe(['bank_transactions'])

def flush_to_clickhouse(batch):
    if not batch:
        return
    
    # ClickHouse expects a list of tuples or lists for bulk insert
    data_to_insert = [
        [
            b['transaction_id'], 
            b['account_id'], 
            b['amount'], 
            b['category'], 
            b['merchant'], 
            b['timestamp']
        ] for b in batch
    ]
    
    try:
        ch_client.insert(
            'transactions', 
            data_to_insert, 
            column_names=['transaction_id', 'account_id', 'amount', 'category', 'merchant', 'event_time']
        )
        print(f"✅ Successfully flushed {len(batch)} transactions to ClickHouse.")
    except Exception as e:
        print(f"❌ ClickHouse insert failed: {e}")
        raise e

def run_consumer():
    buffer = []
    last_flush_time = time.time()
    batch_size_limit = 100
    flush_interval = 5  # seconds

    print("🚀 Consumer started. Waiting for transactions...")

    try:
        while True:
            msg = consumer.poll(1.0) # Poll every 1s

            if msg is None:
                # Check if we should flush due to time even if batch isn't full
                if time.time() - last_flush_time > flush_interval and buffer:
                    flush_to_clickhouse(buffer)
                    consumer.commit() # Commit Kafka offsets after DB write
                    buffer = []
                    last_flush_time = time.time()
                continue

            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                else:
                    print(msg.error())
                    break

            # Add message to buffer
            val = json.loads(msg.value().decode('utf-8'))
            buffer.append(val)

            # Check if we should flush due to batch size
            if len(buffer) >= batch_size_limit:
                flush_to_clickhouse(buffer)
                consumer.commit()
                buffer = []
                last_flush_time = time.time()

    finally:
        consumer.close()

if __name__ == "__main__":
    run_consumer()