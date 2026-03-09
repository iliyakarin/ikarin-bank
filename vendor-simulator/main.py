import os
import uuid
from datetime import date, timedelta
from fastapi import FastAPI, HTTPException, Header, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select

from models import Base, Merchant
from schemas import (
    BillPayValidationRequest,
    BillPayExecuteRequest,
    StatusResponse,
    BillPayExecuteResponse,
    VendorListResponse,
    VendorInfo
)

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL")
SIMULATOR_API_KEY = os.getenv("SIMULATOR_API_KEY")

# Engine & Session
engine = create_async_engine(DATABASE_URL)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

app = FastAPI(title="Vendor Simulator API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware for API Key Auth (optional for some endpoints)
async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != SIMULATOR_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key"
        )
    return x_api_key

# DB Dependency
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

@app.get("/vendors", response_model=VendorListResponse)
async def get_vendors(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Merchant))
    merchants = result.scalars().all()
    
    return VendorListResponse(
        vendors=[
            VendorInfo(
                id=m.merchant_id,
                name=m.name,
                category=m.category,
                email=f"billing@{m.name.lower().replace(' ', '').replace('(', '').replace(')', '')}.com"
            ) for m in merchants
        ]
    )

@app.post("/billpay/validate-subscriber", response_model=StatusResponse, dependencies=[Depends(verify_api_key)])
async def validate_subscriber(payload: BillPayValidationRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Merchant).where(Merchant.merchant_id == payload.merchant_id))
    merchant = result.scalar_one_or_none()
    
    if not merchant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "INVALID_MERCHANT", "message": "Merchant not found"}
        )

    if "00000" in payload.subscriber_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "INVALID_SUBSCRIBER", "message": "Subscriber account not found"}
        )

    return StatusResponse(status="VALIDATED", message=f"Subscriber valid for {merchant.name}")

@app.post("/billpay/execute", response_model=BillPayExecuteResponse, dependencies=[Depends(verify_api_key)])
async def execute_billpay(payload: BillPayExecuteRequest):
    return BillPayExecuteResponse(
        trace_id=str(uuid.uuid4()),
        settlement_date=date.today() + timedelta(days=1)
    )

@app.on_event("startup")
async def startup_event():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
