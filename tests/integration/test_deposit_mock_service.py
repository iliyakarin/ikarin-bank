import importlib.util
import os
import pytest
from httpx import AsyncClient, ASGITransport

mock_main_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../deposit-funds-mock/main.py"))
spec = importlib.util.spec_from_file_location("deposit_funds_mock_main", mock_main_path)
deposit_mock_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(deposit_mock_module)
mock_app = deposit_mock_module.app

@pytest.mark.asyncio
async def test_mock_payment_intent_json():
    transport = ASGITransport(app=mock_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        payload = {
            "amount": 10000,
            "currency": "usd",
            "metadata": {
                "user_id": "5",
                "mode": "payment",
                "type": "deposit"
            }
        }
        res = await ac.post("/v1/payment_intents", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["amount"] == 10000
        assert data["currency"] == "usd"
        assert data["metadata"]["user_id"] == "5"
        assert data["metadata"]["mode"] == "payment"
        assert data["id"].startswith("pi_")

        # Verify get
        get_res = await ac.get(f"/v1/payment_intents/{data['id']}")
        assert get_res.status_code == 200
        get_data = get_res.json()
        assert get_data["amount"] == 10000
        assert get_data["metadata"]["user_id"] == "5"

@pytest.mark.asyncio
async def test_mock_checkout_session_json():
    transport = ASGITransport(app=mock_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        payload = {
            "amount": 10000,
            "currency": "usd",
            "mode": "payment",
            "success_url": "http://localhost:3000/success",
            "cancel_url": "http://localhost:3000/cancel"
        }
        res = await ac.post("/v1/checkout/sessions", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["id"].startswith("cs_test_")
        assert "http://localhost:3000/success" in data["url"]
