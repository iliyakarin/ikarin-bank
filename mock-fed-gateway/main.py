import os
from fastapi import FastAPI, HTTPException, Header, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select

from models import Base, Bank
from schemas import (
    ACHOriginateRequest,
    StatusResponse
)

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    user = os.getenv("FED_GATEWAY_DB_USER")
    password = os.getenv("FED_GATEWAY_DB_PASSWORD")
    host = os.getenv("FED_GATEWAY_DB_HOST")
    db_name = os.getenv("FED_GATEWAY_DB_NAME")
    DATABASE_URL = f"postgresql+asyncpg://{user}:{password}@{host}:5432/{db_name}"

GATEWAY_API_KEY = os.getenv("GATEWAY_API_KEY")

# Engine & Session
engine = create_async_engine(DATABASE_URL)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

app = FastAPI(title="Karin Bank Mock Fed Gateway")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware for API Key Auth
async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != GATEWAY_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key"
        )
    return x_api_key

# DB Dependency
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

@app.post("/fed/ach/originate", response_model=StatusResponse, dependencies=[Depends(verify_api_key)])
async def originate_ach(payload: ACHOriginateRequest, db: AsyncSession = Depends(get_db)):
    # 1. Validate RTN
    result = await db.execute(select(Bank).where(Bank.routing_number == payload.routing_number))
    bank = result.scalar_one_or_none()

    if not bank:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "INVALID_RTN", "message": "Routing number not found"}
        )

    # 2. Failure Injection (R01 - NSF)
    if abs(payload.amount % 1.0 - 0.01) < 0.0001:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": "R01", "message": "Insufficient Funds"}
        )

    return StatusResponse(status="SUCCESS", message=f"ACH Transferred to {bank.name}")

@app.get("/banks")
async def get_banks(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Bank))
    banks = result.scalars().all()
    return {"banks": [{"name": b.name, "routing_number": b.routing_number} for b in banks]}

@app.on_event("startup")
async def startup_event():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seeding banks if empty
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Bank))
        if not result.scalars().first():
            session.add_all([
                Bank(name="Chase", routing_number="021000021"),
                Bank(name="Wells Fargo", routing_number="987654321"),
                Bank(name="Bank of America", routing_number="111222333"),
            ])
            await session.commit()
