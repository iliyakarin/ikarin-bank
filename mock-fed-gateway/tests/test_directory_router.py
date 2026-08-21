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
        assert data["institution"]["fedwire_participant"] is True

@pytest.mark.asyncio
async def test_routing_lookup_invalid_checksum():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/fed/directory/routing/021000029")
        assert res.status_code == 200
        data = res.json()
        assert data["valid"] is False
        assert len(data["errors"]) > 0

@pytest.mark.asyncio
async def test_routing_lookup_unregistered_valid_checksum():
    # 999999990 checksum: 9*3 + 9*7 + ...
    # Let's test an RTN that passes Mod 10 but is not in the directory
    # 011000015 (Boston FRB): 0+7+1+0+0+0+0+7 = 15 -> (10-5)=5.
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/fed/directory/routing/011000015")
        assert res.status_code == 200
        data = res.json()
        assert data["valid"] is False
        assert any("not registered in Federal Reserve Directory" in e for e in data["errors"])

@pytest.mark.asyncio
async def test_directory_search_query_and_pagination():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/fed/directory/institutions?q=Chase&limit=2&offset=0")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] >= 2
        assert len(data["institutions"]) <= 2
        assert all("Chase" in i["name"] for i in data["institutions"])

@pytest.mark.asyncio
async def test_directory_search_filters():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # District filter
        res_d = await ac.get("/fed/directory/institutions?district_id=2")
        assert res_d.status_code == 200
        data_d = res_d.json()
        assert all(i["district_id"] == 2 for i in data_d["institutions"])

        # Capabilities filter
        res_nw = await ac.get("/fed/directory/institutions?fednow_only=true")
        assert res_nw.status_code == 200
        data_nw = res_nw.json()
        assert all(i["fednow_participant"] is True for i in data_nw["institutions"])
