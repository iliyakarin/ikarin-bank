import os
import contextlib
import logging
from fastapi import FastAPI, HTTPException, Header, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from database import init_db, AsyncSessionLocal, get_db
from seed_data import seed_all_data
from models import FederalReserveDistrict, Institution, ACHTransaction, FedwireTransfer, FedNowTransfer
from routers import directory, ach, fedwire, fednow, settlement
from schemas import HealthResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GATEWAY_API_KEY = os.getenv("GATEWAY_API_KEY", "dev_gateway_key_123")

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing Fed Gateway database...")
    await init_db()
    async with AsyncSessionLocal() as session:
        seed_res = await seed_all_data(session)
        logger.info(f"Seeded Federal Reserve Directory: {seed_res}")
    yield

app = FastAPI(
    title="Karin Bank Mock Federal Reserve Gateway",
    description="High-fidelity Federal Reserve banking simulation (FedACH, Fedwire RTGS, FedNow 24/7, E-Payments Directory)",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Key security dependency for sensitive mutation operations
async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != GATEWAY_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Gateway API Key",
        )
    return x_api_key

# Include Routers
app.include_router(directory.router)
app.include_router(ach.router)
app.include_router(fedwire.router)
app.include_router(fednow.router)
app.include_router(settlement.router)

@app.get("/")
async def root():
    return {"status": "ok", "service": "mock-fed-gateway"}

@app.get("/health", response_model=HealthResponse)
async def health(db: AsyncSession = Depends(get_db)):
    dist_count = (await db.execute(select(func.count()).select_from(FederalReserveDistrict))).scalar_one()
    inst_count = (await db.execute(select(func.count()).select_from(Institution))).scalar_one()
    return HealthResponse(
        status="ok",
        districts_count=dist_count,
        institutions_count=inst_count,
    )

@app.get("/fed/status")
async def fed_status(db: AsyncSession = Depends(get_db)):
    dist_count = (await db.execute(select(func.count()).select_from(FederalReserveDistrict))).scalar_one()
    inst_count = (await db.execute(select(func.count()).select_from(Institution))).scalar_one()
    ach_count = (await db.execute(select(func.count()).select_from(ACHTransaction))).scalar_one()
    wire_count = (await db.execute(select(func.count()).select_from(FedwireTransfer))).scalar_one()
    fednow_count = (await db.execute(select(func.count()).select_from(FedNowTransfer))).scalar_one()
    return {
        "status": "OPERATIONAL",
        "system": "Federal Reserve Core Banking Simulator",
        "statistics": {
            "districts": dist_count,
            "institutions": inst_count,
            "ach_transactions": ach_count,
            "fedwire_transfers": wire_count,
            "fednow_transfers": fednow_count,
        },
    }

@app.post("/fed/seed/reset")
async def reset_seed(db: AsyncSession = Depends(get_db)):
    seed_res = await seed_all_data(db)
    return {"status": "re-seeded", "result": seed_res}
