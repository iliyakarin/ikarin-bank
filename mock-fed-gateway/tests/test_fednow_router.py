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
