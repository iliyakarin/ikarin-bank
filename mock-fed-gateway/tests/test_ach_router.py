import pytest
from httpx import AsyncClient, ASGITransport
from main import app

@pytest.mark.asyncio
async def test_ach_originate_success():
    payload = {
        "originator_routing": "123456780",
        "originator_name": "Karin Bank",
        "originator_account": "1001",
        "receiver_routing": "021000021",
        "receiver_name": "Chase Customer",
        "receiver_account": "987654321",
        "amount": 100.00,
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/fed/ach/originate", json=payload, headers={"X-API-KEY": "dev_gateway_key_123"})
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "SETTLED"
        assert data["amount_cents"] == 10000
        assert data["trace_number"] is not None

@pytest.mark.asyncio
async def test_ach_return_r01_nsf():
    payload = {
        "originator_routing": "123456780",
        "receiver_routing": "021000021",
        "receiver_account": "987654321",
        "amount": 100.01,  # .01 triggers R01 NSF
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/fed/ach/originate", json=payload, headers={"X-API-KEY": "dev_gateway_key_123"})
        assert res.status_code == 400
        data = res.json()["detail"]
        assert data["error_code"] == "R01"

@pytest.mark.asyncio
async def test_ach_return_r03_no_account():
    payload = {
        "originator_routing": "123456780",
        "receiver_routing": "021000021",
        "receiver_account": "00000123",  # 00000 triggers R03
        "amount": 50.00,
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/fed/ach/originate", json=payload, headers={"X-API-KEY": "dev_gateway_key_123"})
        assert res.status_code == 400
        data = res.json()["detail"]
        assert data["error_code"] == "R03"

@pytest.mark.asyncio
async def test_ach_batch_origination():
    payload = {
        "originator_routing": "123456780",
        "originator_name": "Karin Bank Payroll",
        "originator_account": "100001",
        "entries": [
            {
                "receiver_routing": "021000021",
                "receiver_name": "Employee 1",
                "receiver_account": "11112222",
                "amount": 2500.00,
                "entry_class": "CREDIT",
            },
            {
                "receiver_routing": "111000012",
                "receiver_name": "Employee 2",
                "receiver_account": "33334444",
                "amount": 3200.00,
                "entry_class": "CREDIT",
            },
        ],
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/fed/ach/batches", json=payload, headers={"X-API-KEY": "dev_gateway_key_123"})
        assert res.status_code == 200
        data = res.json()
        assert data["total_entries"] == 2
        assert data["settled_count"] == 2
        assert data["total_credits_cents"] == 570000
