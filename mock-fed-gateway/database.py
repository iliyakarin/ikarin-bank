import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from models import Base

DATABASE_URL = os.getenv("FED_GATEWAY_DATABASE_URL")
if not DATABASE_URL:
    user = os.getenv("FED_GATEWAY_DB_USER", "fed_gateway_user")
    password = os.getenv("FED_GATEWAY_DB_PASSWORD", "fed_gateway_pass_123")
    host = os.getenv("FED_GATEWAY_DB_HOST", "fed-gateway-db")
    db_name = os.getenv("FED_GATEWAY_DB_NAME", "fed_gateway_db")
    DATABASE_URL = f"postgresql+asyncpg://{user}:{password}@{host}:5432/{db_name}"

engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
