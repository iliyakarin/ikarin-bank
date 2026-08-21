import pytest
from httpx import AsyncClient, ASGITransport
from main import app

@pytest.mark.asyncio
async def test_fedwire_originate_success():
    payload = {
        "sender_routing": "123456780",
        "sender_name": "Karin Bank",
        "sender_account": "1001",
        "receiver_routing": "021000021",
        "receiver_name": "Acme Industrial Corp",
        "receiver_account": "987654321",
        "amount_cents": 50000000,  # $500,000.00
        "business_function_code": "CTR",
        "payment_reference": "INV-10928",
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/fed/wire/originate", json=payload, headers={"X-API-KEY": "dev_gateway_key_123"})
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "SETTLED"
        assert len(data["imad"]) > 10
        assert len(data["omad"]) > 10
        assert data["business_function_code"] == "CTR"

@pytest.mark.asyncio
async def test_fedwire_invalid_routing():
    payload = {
        "sender_routing": "000000000",
        "sender_name": "Bad Sender",
        "sender_account": "1001",
        "receiver_routing": "021000021",
        "receiver_name": "Acme",
        "receiver_account": "987654321",
        "amount_cents": 100000,
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/fed/wire/originate", json=payload, headers={"X-API-KEY": "dev_gateway_key_123"})
        assert res.status_code == 400
