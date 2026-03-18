import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from main import app
from database import User, Account, Transaction
from sqlalchemy import select

client = TestClient(app)

@pytest.fixture
def mock_deposit_router():
    with patch("routers.deposit.stripe") as mock:
        yield mock

@pytest.fixture
def mock_deposit_service():
    with patch("routers.deposit.handle_checkout_completed") as mock_checkout, \
         patch("routers.deposit.handle_subscription_deleted") as mock_sub:
        yield mock_checkout, mock_sub

def test_create_checkout_session(token, mock_deposit_router):
    # Mock stripe.checkout.Session.create
    mock_deposit_router.checkout.Session.create.return_value = MagicMock(
        id="sess_123",
        url="https://checkout.stripe.com/pay/sess_123"
    )

    response = client.post(
        "/api/v1/deposits/create-checkout-session",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "amount": 1000,
            "currency": "usd",
            "mode": "payment",
            "success_url": "http://localhost:3000/success",
            "cancel_url": "http://localhost:3000/cancel"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "sess_123"
    assert data["url"] == "https://checkout.stripe.com/pay/sess_123"
    mock_deposit_router.checkout.Session.create.assert_called_once()


def test_create_portal_session(token, mock_deposit_router):
    # Mock stripe.Customer.list and stripe.billing_portal.Session.create
    mock_deposit_router.Customer.list.return_value = MagicMock(data=[MagicMock(id="cus_123")])
    mock_deposit_router.billing_portal.Session.create.return_value = MagicMock(
        url="https://billing.stripe.com/p/session/123"
    )

    response = client.post(
        "/api/v1/deposits/create-portal-session",
        headers={"Authorization": f"Bearer {token}"},
        json={"return_url": "http://localhost:3000/client"}
    )

    assert response.status_code == 200
    assert response.json()["url"] == "https://billing.stripe.com/p/session/123"


def test_webhook_signature_verification_failure(mock_deposit_router):
    # Mock stripe.Webhook.construct_event to raise error
    mock_deposit_router.Webhook.construct_event.side_effect = ValueError("Invalid signature")

    response = client.post(
        "/api/v1/deposits/webhook",
        headers={"Stripe-Signature": "invalid"},
        content="raw_payload"
    )

    assert response.status_code == 400
    assert "Invalid payload" in response.json()["detail"]


@patch("routers.deposit.WEBHOOK_SECRET", "whsec_test")
def test_webhook_checkout_completed(mock_deposit_router, mock_deposit_service):
    mock_checkout, _ = mock_deposit_service
    
    # Mock event
    event = {
        "type": "checkout.session.completed",
        "data": {"object": {"id": "sess_123"}},
        "id": "evt_123"
    }
    mock_deposit_router.Webhook.construct_event.return_value = event

    response = client.post(
        "/api/v1/deposits/webhook",
        headers={"Stripe-Signature": "v1=valid"},
        content="raw_payload"
    )

    assert response.status_code == 200
    mock_checkout.assert_called_once()
