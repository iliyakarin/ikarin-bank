import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from decimal import Decimal

@pytest.fixture
def mock_user():
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.email = "test@example.com"
    mock_user.role = "user"
    return mock_user

@pytest.fixture
def mock_db():
    return AsyncMock()

@pytest.fixture
def mock_gateway_client():
    with patch("routers.deposit.gateway_client", new_callable=MagicMock) as mock:
        mock.post = AsyncMock()
        mock.get = AsyncMock()
        yield mock

@pytest.fixture
def mock_deposit_service():
    with patch("routers.deposit.handle_checkout_completed", new_callable=AsyncMock) as mock_checkout, \
         patch("routers.deposit.handle_subscription_deleted", new_callable=AsyncMock) as mock_sub:
        yield mock_checkout, mock_sub

@pytest.mark.asyncio
async def test_create_checkout_session(mock_fastapi_dependency, mock_user, mock_db, mock_gateway_client):
    main_module = mock_fastapi_dependency
    
    mock_gateway_client.post.return_value = {
        "id": "sess_123",
        "url": "https://checkout.stripe.com/pay/sess_123"
    }

    from schemas.deposit import CheckoutSessionCreate
    payload = CheckoutSessionCreate(
        amount=1000,
        currency="usd",
        mode="payment",
        success_url="http://localhost:3000/success",
        cancel_url="http://localhost:3000/cancel"
    )

    response = await main_module.create_checkout_session(
        payload=payload,
        current_user=mock_user
    )

    assert response.id == "sess_123"
    assert response.url == "https://checkout.stripe.com/pay/sess_123"
    mock_gateway_client.post.assert_called_once()

@pytest.mark.asyncio
async def test_create_portal_session(mock_fastapi_dependency, mock_user, mock_gateway_client):
    main_module = mock_fastapi_dependency
    
    def side_effect(path, data=None, params=None):
        if path == "/v1/customers":
            return {"data": [{"id": "cus_123"}]}
        if path == "/v1/billing_portal/sessions":
            return {"url": "https://billing.stripe.com/p/session/123"}
        return {}

    mock_gateway_client.get.side_effect = side_effect
    mock_gateway_client.post.side_effect = side_effect

    from schemas.deposit import PortalSessionCreate
    payload = PortalSessionCreate(return_url="http://localhost:3000/client")

    response = await main_module.create_portal_session(
        payload=payload,
        current_user=mock_user
    )

    assert response.url == "https://billing.stripe.com/p/session/123"

@pytest.mark.asyncio
async def test_webhook_checkout_completed(mock_fastapi_dependency, mock_db, mock_deposit_service):
    main_module = mock_fastapi_dependency
    mock_checkout, _ = mock_deposit_service

    event_data = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "sess_123",
                "amount": 1000,
                "metadata": {"user_id": "1", "mode": "payment"}
            }
        }
    }
    
    # Mock request object for webhook
    mock_request = MagicMock()
    mock_request.json = AsyncMock(return_value=event_data)

    response = await main_module.deposit_webhook(
        request=mock_request,
        db=mock_db
    )

    assert response["status"] == "success"
    mock_checkout.assert_called_once()

@pytest.mark.asyncio
async def test_create_payment_intent(mock_fastapi_dependency, mock_user, mock_db, mock_gateway_client):
    main_module = mock_fastapi_dependency
    
    # Mock idempotency check (not found)
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = None
    mock_db.execute.return_value = mock_result
    
    from schemas.deposit import PaymentIntentCreate
    payload = PaymentIntentCreate(amount=1500)
    
    mock_gateway_client.post.return_value = {"id": "pi_123", "client_secret": "sk_123", "status": "requires_payment_method"}
    
    response = await main_module.create_payment_intent(
        payload=payload,
        db=mock_db,
        current_user=mock_user
    )
    
    assert response.id == "pi_123"
    assert response.status == "requires_payment_method"

@pytest.mark.asyncio
async def test_confirm_payment_intent(mock_fastapi_dependency, mock_user, mock_db, mock_gateway_client):
    main_module = mock_fastapi_dependency
    
    # Mock idempotency check (not found)
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = None
    mock_db.execute.return_value = mock_result
    
    intent_id = "pi_123"
    from schemas.deposit import PaymentIntentConfirm
    payload = PaymentIntentConfirm(payment_method="pm_123")
    
    mock_request = MagicMock()
    mock_request.headers.get.return_value = "idem_123"
    
    mock_gateway_client.get.return_value = {"id": "pi_123", "amount": 1000}
    
    with patch("routers.deposit.handle_checkout_completed", new_callable=AsyncMock) as mock_handle:
        response = await main_module.confirm_payment_intent(
            intent_id=intent_id,
            payload=payload,
            request=mock_request,
            db=mock_db,
            current_user=mock_user
        )
        
    assert response.status == "succeeded"
    assert response.id == "pi_123"
    mock_handle.assert_called_once()
