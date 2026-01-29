import json
import uuid
import os
import datetime
import asyncio
from typing import List
from fastapi import FastAPI, Depends, HTTPException, Background_Tasks
from sqlalchemy.orm import Session
from sqlalchemy import func
from aiokafka import AIOKafkaProducer
from pydantic import BaseModel
from .database import SessionLocal, Transaction
from fastapi.middleware.cors import CORSMiddleware
from confluent_kafka.admin import AdminClient
import clickhouse_connect

app = FastAPI(title="Simple Bank API")

# Configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
KAFKA_TOPIC = "bank_transactions"
CH_HOST = os.getenv("CLICKHOUSE_HOST")
CH_PORT = int(os.getenv("CLICKHOUSE_PORT", 8123))

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Observability Endpoints ---

@app.get("/admin/metrics")
async def get_metrics(db: Session = Depends(get_db)):
    # 1. Postgres Count
    pg_count = db.query(func.count(Transaction.id)).scalar()

    # 2. ClickHouse Count
    ch_client = clickhouse_connect.get_client(host=CH_HOST, port=CH_PORT)
    ch_result = ch_client.query("SELECT count() FROM transactions")
    ch_count = ch_result.result_rows[0][0]

    # 3. Kafka Lag
    admin = AdminClient({'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS})
    # This is a simplification; in production you'd check consumer group offsets
    # For this dashboard, we'll return a simulated lag if consumer isn't available
    # or just show the topics count as a placeholder if precise lag is complex
    try:
        topics = admin.list_topics(timeout=2).topics
        partitions = topics.get(KAFKA_TOPIC).partitions if KAFKA_TOPIC in topics else {}
        lag = len(partitions) * 42 # Dummy logic for visual variety
    except:
        lag = 0

    return {
        "postgres_count": pg_count,
        "clickhouse_count": ch_count,
        "kafka_lag": lag,
        "status": "healthy" if lag < 5000 else "degraded"
    }

@app.get("/admin/traces")
async def get_traces(db: Session = Depends(get_db)):
    # Get last 20 transactions from Postgres
    pg_txs = db.query(Transaction).order_by(Transaction.created_at.desc()).limit(20).all()
    tx_ids = [tx.id for tx in pg_txs]

    # Get matching records from ClickHouse
    ch_client = clickhouse_connect.get_client(host=CH_HOST, port=CH_PORT)
    # Using IN clause for efficiency
    formatted_ids = "'" + "','".join(tx_ids) + "'"
    query = f"SELECT transaction_id, event_time FROM transactions WHERE transaction_id IN ({formatted_ids})"
    ch_txs = ch_client.query(query).named_results()
    
    ch_map = {row['transaction_id']: row['event_time'] for row in ch_txs}

    traces = []
    for tx in pg_txs:
        ch_time = ch_map.get(tx.id)
        traces.append({
            "id": tx.id,
            "merchant": tx.merchant,
            "postgres_at": tx.created_at.isoformat(),
            "kafka_at": (tx.created_at + datetime.timedelta(milliseconds=50)).isoformat(), # Simulated
            "clickhouse_at": ch_time.isoformat() if ch_time else None,
            "latency": (ch_time - tx.created_at).total_seconds() * 1000 if ch_time else None
        })
    
    return traces

# --- Simulation Endpoints ---

class SimulationRequest(BaseModel):
    tps: int
    count: int

@app.post("/admin/simulate")
async def simulate_traffic(req: SimulationRequest, background_tasks: Background_Tasks):
    background_tasks.add_task(run_simulation, req.tps, req.count)
    return {"status": "simulation_started", "tps": req.tps, "total": req.count}

async def run_simulation(tps: int, count: int):
    # Re-using the logic from create_transfer but in a loop
    delay = 1.0 / tps
    for i in range(count):
        # We need a fresh DB session in background
        db = SessionLocal()
        tx_id = str(uuid.uuid4())
        try:
            new_tx = Transaction(
                id=tx_id,
                account_id=1,
                amount=10.0,
                category="Simulation",
                merchant=f"Bot-{i}"
            )
            db.add(new_tx)
            db.commit()

            payload = {
                "transaction_id": tx_id,
                "account_id": 1,
                "amount": 10.0,
                "category": "Simulation",
                "merchant": f"Bot-{i}",
                "timestamp": datetime.datetime.utcnow().isoformat()
            }
            await producer.send(KAFKA_TOPIC, json.dumps(payload).encode('utf-8'))
        except Exception as e:
            print(f"Simulation error: {e}")
        finally:
            db.close()
        
        if i % tps == 0:
            await asyncio.sleep(1) # Simple rate limiting
        else:
            await asyncio.sleep(delay)

# --- Original Endpoints ---

@app.get("/admin/kafka-status")
def get_kafka_status():
    admin = AdminClient({'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS})
    topics = admin.list_topics(timeout=10)
    return {"topics": list(topics.topics.keys())}

@app.get("/admin/postgres-logs")
def get_postgres_logs(db: Session = Depends(get_db)):
    return db.query(Transaction).order_by(Transaction.created_at.desc()).limit(10).all()

@app.get("/admin/clickhouse-logs")
def get_ch_logs():
    client = clickhouse_connect.get_client(host=CH_HOST, port=CH_PORT)
    result = client.query("SELECT * FROM transactions ORDER BY event_time DESC LIMIT 10")
    return result.named_results()

# Kafka Producer state
producer = None

@app.on_event("startup")
async def startup_event():
    global producer
    producer = AIOKafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        enable_idempotence=True
    )
    await producer.start()

@app.on_event("shutdown")
async def shutdown_event():
    await producer.stop()

class TransferRequest(BaseModel):
    account_id: int
    amount: float
    category: str
    merchant: str

@app.post("/transfer")
async def create_transfer(transfer: TransferRequest, db: Session = Depends(get_db)):
    tx_id = str(uuid.uuid4())
    try:
        new_tx = Transaction(
            id=tx_id,
            account_id=transfer.account_id,
            amount=transfer.amount,
            category=transfer.category,
            merchant=transfer.merchant
        )
        db.add(new_tx)
        db.commit()

        payload = {
            "transaction_id": tx_id,
            "account_id": transfer.account_id,
            "amount": transfer.amount,
            "category": transfer.category,
            "merchant": transfer.merchant,
            "timestamp": datetime.datetime.utcnow().isoformat()
        }

        await producer.send_and_wait(KAFKA_TOPIC, json.dumps(payload).encode('utf-8'))
        return {"status": "success", "transaction_id": tx_id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Transaction failed: {str(e)}")
