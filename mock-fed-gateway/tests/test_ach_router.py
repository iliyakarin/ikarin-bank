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
        tx_id = data["id"]

        # Verify querying the created transaction
        get_res = await ac.get(f"/fed/ach/transactions/{tx_id}")
        assert get_res.status_code == 200
        assert get_res.json()["id"] == tx_id

@pytest.mark.asyncio
async def test_ach_get_transaction_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/fed/ach/transactions/nonexistent-id-12345")
        assert res.status_code == 404

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
async def test_ach_return_r02_closed_account():
    payload = {
        "originator_routing": "123456780",
        "receiver_routing": "021000021",
        "receiver_account": "987654321",
        "amount": 100.02,  # .02 triggers R02 Closed
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/fed/ach/originate", json=payload, headers={"X-API-KEY": "dev_gateway_key_123"})
        assert res.status_code == 400
        assert res.json()["detail"]["error_code"] == "R02"

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
async def test_ach_return_r08_payment_stopped():
    payload = {
        "originator_routing": "123456780",
        "receiver_routing": "021000021",
        "receiver_account": "987654321",
        "amount": 100.08,  # .08 triggers R08
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/fed/ach/originate", json=payload, headers={"X-API-KEY": "dev_gateway_key_123"})
        assert res.status_code == 400
        assert res.json()["detail"]["error_code"] == "R08"

@pytest.mark.asyncio
async def test_ach_return_r10_unauthorized():
    payload = {
        "originator_routing": "123456780",
        "receiver_routing": "021000021",
        "receiver_account": "987654321",
        "amount": 100.10,  # .10 triggers R10
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/fed/ach/originate", json=payload, headers={"X-API-KEY": "dev_gateway_key_123"})
        assert res.status_code == 400
        assert res.json()["detail"]["error_code"] == "R10"

@pytest.mark.asyncio
async def test_ach_return_r16_frozen_and_r20():
    payload_r16 = {
        "originator_routing": "123456780",
        "receiver_routing": "021000021",
        "receiver_account": "987654321",
        "amount": 100.16,
    }
    payload_r20 = {
        "originator_routing": "123456780",
        "receiver_routing": "021000021",
        "receiver_account": "987654321",
        "amount": 100.20,
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res16 = await ac.post("/fed/ach/originate", json=payload_r16, headers={"X-API-KEY": "dev_gateway_key_123"})
        assert res16.status_code == 400
        assert res16.json()["detail"]["error_code"] == "R16"

        res20 = await ac.post("/fed/ach/originate", json=payload_r20, headers={"X-API-KEY": "dev_gateway_key_123"})
        assert res20.status_code == 400
        assert res20.json()["detail"]["error_code"] == "R20"

@pytest.mark.asyncio
async def test_ach_header_override():
    payload = {
        "originator_routing": "123456780",
        "receiver_routing": "021000021",
        "receiver_account": "987654321",
        "amount": 50.00,
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post(
            "/fed/ach/originate",
            json=payload,
            headers={"X-API-KEY": "dev_gateway_key_123", "x-fed-simulate-return": "R06"},
        )
        assert res.status_code == 400
        assert res.json()["detail"]["error_code"] == "R06"

@pytest.mark.asyncio
async def test_ach_invalid_routing_not_found():
    payload = {
        "originator_routing": "123456780",
        "receiver_routing": "000000000",
        "receiver_account": "987654321",
        "amount": 50.00,
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/fed/ach/originate", json=payload, headers={"X-API-KEY": "dev_gateway_key_123"})
        assert res.status_code == 400
        assert res.json()["detail"]["error_code"] == "R04"

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
            {
                "receiver_routing": "021000021",
                "receiver_name": "Bad Employee",
                "receiver_account": "00000444",
                "amount": 1000.00,
                "entry_class": "CREDIT",
            },
        ],
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/fed/ach/batches", json=payload, headers={"X-API-KEY": "dev_gateway_key_123"})
        assert res.status_code == 200
        data = res.json()
        assert data["total_entries"] == 3
        assert data["settled_count"] == 2
        assert data["returned_count"] == 1
        assert data["total_credits_cents"] == 670000
