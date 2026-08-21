import pytest
from httpx import AsyncClient, ASGITransport
from main import app

@pytest.mark.asyncio
async def test_fednow_transfer_accp():
    payload = {
        "debtor_routing": "123456780",
        "debtor_name": "Ikarin",
        "debtor_account": "1001",
        "creditor_routing": "111000012",
        "creditor_name": "Alex",
        "creditor_account": "2002",
        "amount_cents": 2500,
        "remittance_info": "Dinner Split",
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/fed/fednow/transfer", json=payload, headers={"X-API-KEY": "dev_gateway_key_123"})
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ACCP"
        assert data["end_to_end_id"] is not None
        e2e_id = data["end_to_end_id"]

        # Verify querying FedNow transfer
        get_res = await ac.get(f"/fed/fednow/transfers/{e2e_id}")
        assert get_res.status_code == 200
        assert get_res.json()["end_to_end_id"] == e2e_id

@pytest.mark.asyncio
async def test_fednow_get_transfer_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/fed/fednow/transfers/NONEXISTENT-E2E-ID")
        assert res.status_code == 404

@pytest.mark.asyncio
async def test_fednow_transfer_rjct():
    payload = {
        "debtor_routing": "123456780",
        "debtor_name": "Ikarin",
        "debtor_account": "1001",
        "creditor_routing": "111000012",
        "creditor_name": "Alex",
        "creditor_account": "00001234",  # 0000 triggers RJCT
        "amount_cents": 2500,
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/fed/fednow/transfer", json=payload, headers={"X-API-KEY": "dev_gateway_key_123"})
        assert res.status_code == 400
        data = res.json()["detail"]
        assert data["status"] == "RJCT"
        assert data["status_reason_code"] == "AC04"

@pytest.mark.asyncio
async def test_fednow_rfp():
    payload = {
        "debtor_routing": "123456780",
        "debtor_name": "Ikarin",
        "creditor_routing": "021000021",
        "creditor_name": "Supplier Corp",
        "amount_cents": 150000,
        "remittance_info": "Invoice #9001",
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/fed/fednow/rfp", json=payload, headers={"X-API-KEY": "dev_gateway_key_123"})
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "PRESENTED_TO_DEBTOR"
        assert data["amount_cents"] == 150000
