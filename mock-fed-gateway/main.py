import os
import random
import uuid
from datetime import date, timedelta
from fastapi import FastAPI, HTTPException, Header, Depends, status
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select

from models import Base, Bank, Merchant
from schemas import (
    ACHOriginateRequest, 
    BillPayValidationRequest, 
    BillPayExecuteRequest, 
    StatusResponse,
    BillPayExecuteResponse
)

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL")
GATEWAY_API_KEY = os.getenv("GATEWAY_API_KEY")

# Engine & Session
engine = create_async_engine(DATABASE_URL)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

app = FastAPI(title="Karin Bank Mock Fed Gateway")

# Middleware-ish dependency for API Key Auth
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
    # If amount ends in .01 (e.g., 100.01)
    if abs(payload.amount % 1.0 - 0.01) < 0.0001:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": "R01", "message": "Insufficient Funds"}
        )

    return StatusResponse(status="SUCCESS", message=f"ACH Transferred to {bank.name}")

@app.post("/billpay/validate-subscriber", response_model=StatusResponse, dependencies=[Depends(verify_api_key)])
async def validate_subscriber(payload: BillPayValidationRequest, db: AsyncSession = Depends(get_db)):
    # 1. Validate Merchant
    result = await db.execute(select(Merchant).where(Merchant.merchant_id == payload.merchant_id))
    merchant = result.scalar_one_or_none()
    
    if not merchant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "INVALID_MERCHANT", "message": "Merchant not found"}
        )

    # 2. Failure Injection (R03 - No Account)
    if "00000" in payload.subscriber_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "INVALID_SUBSCRIBER", "message": "Subscriber account not found"}
        )

    return StatusResponse(status="VALIDATED", message=f"Subscriber valid for {merchant.name}")

@app.post("/billpay/execute", response_model=BillPayExecuteResponse, dependencies=[Depends(verify_api_key)])
async def execute_billpay(payload: BillPayExecuteRequest):
    # Simulate jitter is handled by network simulation as per requirements
    return BillPayExecuteResponse(
        trace_id=str(uuid.uuid4()),
        settlement_date=date.today() + timedelta(days=1)
    )

@app.on_event("startup")
async def startup_event():
    # Attempt to create tables if they don't exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
