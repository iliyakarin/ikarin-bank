import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock
import uuid
from decimal import Decimal

@pytest.mark.asyncio
async def test_create_payment_intent(mock_fastapi_dependency):
    import main
    import routers.stripe as stripe_router
    from schemas.stripe_mock import PaymentIntentCreate
    
    mock_db = MagicMock()
    mock_db.execute = AsyncMock()
    mock_db.commit = AsyncMock()

    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.email = "test@test.com"
    
    payload = PaymentIntentCreate(amount=Decimal("1500"))
    
    fn = getattr(stripe_router.create_payment_intent, "__wrapped__", stripe_router.create_payment_intent)
    res = await fn(payload=payload, db=mock_db, current_user=mock_user)
    
    assert res.client_secret is not None
    assert res.status == "requires_payment_method"


@pytest.mark.asyncio
async def test_create_payment_method(mock_fastapi_dependency):
    import main
    import routers.stripe as stripe_router
    from schemas.stripe_mock import PaymentMethodCreate
    
    mock_db = MagicMock()
    mock_db.execute = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()
    
    # Mocking db.execute to return main_account
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    
    main_account = MagicMock()
    main_account.id = 123
    
    mock_scalars.first.return_value = main_account
    mock_result.scalars.return_value = mock_scalars
    mock_db.execute.return_value = mock_result
    
    mock_user = MagicMock()
    mock_user.id = 1
    
    payload = PaymentMethodCreate(
        card_number="4242424242424242",
        exp_month="12",
        exp_year="2030",
        cvc="123",
        name="Jane Doe"
    )
    
    fn = getattr(stripe_router.create_payment_method, "__wrapped__", stripe_router.create_payment_method)
    res = await fn(payload=payload, db=mock_db, current_user=mock_user)
    
    assert res.id.startswith("pm_")
    assert res.card.last4 == "4242"


@pytest.mark.asyncio
async def test_confirm_payment_intent(mock_fastapi_dependency):
    import main
    import routers.stripe as stripe_router
    from schemas.stripe_mock import PaymentIntentConfirm
    
    mock_db = MagicMock()
    mock_db.execute = AsyncMock()
    mock_db.commit = AsyncMock()
    
    mock_user = MagicMock()
    mock_user.id = 1
    
    intent_id = "pi_" + uuid.uuid4().hex
    idem_key = uuid.uuid4().hex
    
    payload = PaymentIntentConfirm(payment_method="pm_mock123")
    
    mock_request = MagicMock()
    mock_request.headers.get = MagicMock(return_value=idem_key)
    
    # First execute call -> idempotency key check
    # Second execute call -> Account fetch
    
    call_idx = [0]
    def execute_side_effect(*args, **kwargs):
        idx = call_idx[0]
        call_idx[0] += 1
        
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        
        if idx == 0:
            mock_scalars.first.return_value = None # Idempotency key not found
        elif idx == 1:
            main_acc = MagicMock()
            main_acc.id = 123
            main_acc.balance = Decimal("100.00")
            mock_scalars.first.return_value = main_acc # Account
            
        mock_result.scalars.return_value = mock_scalars
        return mock_result

    mock_db.execute.side_effect = execute_side_effect

    fn = getattr(stripe_router.confirm_payment_intent, "__wrapped__", stripe_router.confirm_payment_intent)
        
    res = await fn(intent_id=intent_id, payload=payload, request=mock_request, db=mock_db, current_user=mock_user)
    
    assert res.status == "succeeded"
    assert res.id == intent_id

