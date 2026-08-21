import pytest
from httpx import AsyncClient, ASGITransport
from main import app

@pytest.mark.asyncio
async def test_get_districts():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/fed/districts")
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 12
        assert any(d["name"] == "Federal Reserve Bank of New York" for d in data)
        assert any(d["district_letter"] == "L" for d in data)

@pytest.mark.asyncio
async def test_get_banks_compat():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/banks")
        assert res.status_code == 200
        data = res.json()
        assert "banks" in data
        assert len(data["banks"]) >= 30
        names = [b["name"] for b in data["banks"]]
        assert any("Chase" in name for name in names)
        assert any("Karin" in name for name in names)

@pytest.mark.asyncio
async def test_routing_lookup_valid():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/fed/directory/routing/021000021")
        assert res.status_code == 200
        data = res.json()
        assert data["valid"] is True
        assert data["institution"]["name"] == "JPMorgan Chase Bank, N.A."
        assert data["district"]["name"] == "Federal Reserve Bank of New York"

@pytest.mark.asyncio
async def test_routing_lookup_invalid_checksum():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/fed/directory/routing/021000029")
        assert res.status_code == 200
        data = res.json()
        assert data["valid"] is False
        assert len(data["errors"]) > 0

@pytest.mark.asyncio
async def test_directory_search_query():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/fed/directory/institutions?q=Chase")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] >= 1
        assert all("Chase" in i["name"] for i in data["institutions"])

@pytest.mark.asyncio
async def test_directory_search_by_state():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/fed/directory/institutions?state=CA")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] >= 1
        assert all(i["state"] == "CA" for i in data["institutions"])
