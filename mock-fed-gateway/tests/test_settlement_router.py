import pytest
from httpx import AsyncClient, ASGITransport
from main import app

@pytest.mark.asyncio
async def test_get_master_account():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/fed/master-account/123456780")
        assert res.status_code == 200
        data = res.json()
        assert data["routing_number"] == "123456780"
        assert data["balance_cents"] > 0
        assert data["status"] == "OPEN"

@pytest.mark.asyncio
async def test_get_master_account_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/fed/master-account/000000000")
        assert res.status_code == 404

@pytest.mark.asyncio
async def test_adjust_master_account():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        payload = {
            "routing_number": "123456780",
            "adjustment_cents": 5000000,
            "reason": "Test reserve injection",
        }
        res = await ac.post("/fed/master-account/adjust", json=payload, headers={"X-API-KEY": "dev_gateway_key_123"})
        assert res.status_code == 200
        data = res.json()
        assert data["balance_cents"] > 1_000_000_000

@pytest.mark.asyncio
async def test_adjust_master_account_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        payload = {
            "routing_number": "000000000",
            "adjustment_cents": 5000000,
            "reason": "Test non-existent",
        }
        res = await ac.post("/fed/master-account/adjust", json=payload, headers={"X-API-KEY": "dev_gateway_key_123"})
        assert res.status_code == 404

@pytest.mark.asyncio
async def test_get_daily_statement():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/fed/statements/123456780")
        assert res.status_code == 200
        data = res.json()
        assert data["routing_number"] == "123456780"
        assert "opening_balance_cents" in data
        assert "closing_balance_cents" in data

@pytest.mark.asyncio
async def test_get_daily_statement_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/fed/statements/000000000")
        assert res.status_code == 404

@pytest.mark.asyncio
async def test_health_and_status_and_reset():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ok"
        assert data["districts_count"] == 12
        assert data["institutions_count"] >= 30

        res_stat = await ac.get("/fed/status")
        assert res_stat.status_code == 200
        stat_data = res_stat.json()
        assert stat_data["status"] == "OPERATIONAL"

        res_reset = await ac.post("/fed/seed/reset")
        assert res_reset.status_code == 200
        assert res_reset.json()["status"] == "re-seeded"
