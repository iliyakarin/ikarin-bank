import pytest
import pytest_asyncio
import sys
import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models import Base
from seed_data import seed_all_data
from database import get_db
from main import app

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture(scope="function")
async def test_engine():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()

@pytest_asyncio.fixture(scope="function")
async def test_db_session(test_engine):
    async_session = async_sessionmaker(test_engine, expire_on_commit=False)
    async with async_session() as session:
        await seed_all_data(session)
        yield session

@pytest_asyncio.fixture(autouse=True)
async def override_get_db(test_db_session):
    async def _get_test_db():
        yield test_db_session

    app.dependency_overrides[get_db] = _get_test_db
    yield
    app.dependency_overrides.pop(get_db, None)
