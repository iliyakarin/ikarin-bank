import pytest
import asyncio
import uuid
import os
import httpx
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from unittest.mock import patch, AsyncMock

# Import app modules
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from main import app
from database import Base, User, Account
from auth_utils import get_db, create_access_token
from config import settings

# Override DB host for local integration tests
DB_URL = settings.DATABASE_URL.replace("@postgres:", "@localhost:")

@pytest.fixture
async def session_factory():
    # Create engine and factory within the fixture to ensure loop binding
    engine = create_async_engine(DB_URL, echo=False)
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    yield factory
    await engine.dispose()

@pytest.fixture(autouse=True)
def mock_startup():
    with patch("main.run_all_migrations", new_callable=AsyncMock) as m_run, \
         patch("main.AIOKafkaProducer") as m_kafka:
        
        instance = m_kafka.return_value
        instance.start = AsyncMock()
        instance.stop = AsyncMock()
        yield m_kafka

@pytest.fixture
async def db_session(session_factory):
    async with session_factory() as session:
        yield session
        await session.rollback()

@pytest.fixture
async def client(session_factory):
    async def override_get_db():
        async with session_factory() as session:
            yield session
    
    app.dependency_overrides[get_db] = override_get_db
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()

async def create_test_user(db: AsyncSession, email: str, balance: int = 10000):
    user = User(
        first_name="Security",
        last_name="Test",
        email=email,
        password_hash="mock_hash"
    )
    db.add(user)
    await db.flush()
    
    account = Account(
        user_id=user.id,
        is_main=True,
        name="Main Account",
        balance=balance,
        routing_number="123456789",
        account_number_encrypted="enc_test",
        account_number_last_4="1234",
        internal_reference_id=str(uuid.uuid4()),
        account_uuid=str(uuid.uuid4())
    )
    db.add(account)
    # We need to commit so the app sees the data if it uses a different session
    await db.commit()
    return user, account

@pytest.mark.asyncio
async def test_idor_account_access(client: httpx.AsyncClient, db_session: AsyncSession):
    """Verify that a user cannot access another user's account details."""
    user_a, acc_a = await create_test_user(db_session, f"a_{uuid.uuid4()}@idor.com")
    user_b, acc_b = await create_test_user(db_session, f"b_{uuid.uuid4()}@idor.com")
    
    token_a = create_access_token({"sub": user_a.email})
    headers = {"Authorization": f"Bearer {token_a}"}
    
    response = await client.get(f"/v1/accounts/{acc_b.id}/credentials", headers=headers)
    assert response.status_code == 404
    assert "access denied" in response.json().get("detail", "").lower()

@pytest.mark.asyncio
async def test_p2p_idempotency_router(client: httpx.AsyncClient, db_session: AsyncSession, session_factory):
    """Verify that multiple requests with the same idempotency key only result in one transfer."""
    user_a, acc_a = await create_test_user(db_session, f"source_{uuid.uuid4()}@test.com", 10000)
    user_b, acc_b = await create_test_user(db_session, f"dest_{uuid.uuid4()}@test.com", 1000)
    
    token_a = create_access_token({"sub": user_a.email})
    headers = {"Authorization": f"Bearer {token_a}"}
    
    id_key = f"key-{uuid.uuid4()}"
    payload = {
        "recipient_email": user_b.email,
        "amount": 2000,
        "source_account_id": acc_a.id,
        "idempotency_key": id_key,
        "commentary": "Idempotency test"
    }
    
    with patch("services.transfer_service.emit_activity"), \
         patch("services.transfer_service.get_vendors", return_value=[]), \
         patch("routers.transfers.emit_activity"):
        # First request
        resp1 = await client.post("/v1/p2p-transfer", json=payload, headers=headers)
        assert resp1.status_code == 200
        
        # Second request (same key)
        resp2 = await client.post("/v1/p2p-transfer", json=payload, headers=headers)
        assert resp2.status_code == 200
        assert resp2.json()["transaction_id"] == resp1.json()["transaction_id"]
        
        # Verify balance only decreased ONCE
        async with session_factory() as fresh_db:
             from sqlalchemy import select
             result = await fresh_db.execute(select(Account).filter(Account.id == acc_a.id))
             acc = result.scalars().first()
             assert acc.balance == 8000
