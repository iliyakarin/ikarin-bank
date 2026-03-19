import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock
import uuid
from decimal import Decimal

@pytest.mark.asyncio
async def test_create_payment_intent(mock_fastapi_dependency):
    import main
    import routers.deposit as deposit_router
    from schemas.deposit_mock import PaymentIntentCreate

    mock_db = MagicMock()
    mock_db.execute = AsyncMock()
    mock_db.commit = AsyncMock()

    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.email = "test@test.com"

    payload = PaymentIntentCreate(amount=Decimal("1500"))

    fn = getattr(deposit_router.create_payment_intent, "__wrapped__", deposit_router.create_payment_intent)
    res = await fn(payload=payload, db=mock_db, current_user=mock_user)

    assert res.client_secret is not None
    assert res.status == "requires_payment_method"

@pytest.mark.asyncio
async def test_create_subscription_intent_prevents_double_sub(mock_fastapi_dependency):
    import routers.deposit as deposit_router
    from schemas.deposit_mock import PaymentIntentCreate
    from database import Subscription

    mock_db = MagicMock()
    mock_db.execute = AsyncMock()

    mock_user = MagicMock()
    mock_user.id = 1

    payload = PaymentIntentCreate(amount=Decimal("4900"))

    # Mocking active sub check
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.first.return_value = Subscription(id=1, status="active")
    mock_result.scalars.return_value = mock_scalars
    mock_db.execute.return_value = mock_result

    from fastapi import HTTPException, status
    fn = getattr(deposit_router.create_payment_intent, "__wrapped__", deposit_router.create_payment_intent)

    with pytest.raises(HTTPException) as exc:
        await fn(payload=payload, db=mock_db, current_user=mock_user)
    assert exc.value.status_code == 400
    assert "User already subscribed" in exc.value.detail


@pytest.mark.asyncio
async def test_create_payment_method(mock_fastapi_dependency):
    import main
    import routers.deposit as deposit_router
    from schemas.deposit_mock import PaymentMethodCreate

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

    fn = getattr(deposit_router.create_payment_method, "__wrapped__", deposit_router.create_payment_method)
    res = await fn(payload=payload, db=mock_db, current_user=mock_user)

    assert res.id.startswith("pm_")
    assert res.card.last4 == "4242"


@pytest.mark.asyncio
async def test_confirm_payment_intent(mock_fastapi_dependency):
    import main
    import routers.deposit as deposit_router
    from schemas.deposit_mock import PaymentIntentConfirm

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
            class MockAccount:
                def __init__(self):
                    self.id = 123
                    self.balance = Decimal("100.00")
            main_acc = MockAccount()
            mock_scalars.first.return_value = main_acc # Account

        mock_result.scalars.return_value = mock_scalars
        return mock_result

    mock_db.execute.side_effect = execute_side_effect

    fn = getattr(deposit_router.confirm_payment_intent, "__wrapped__", deposit_router.confirm_payment_intent)

    res = await fn(intent_id=intent_id, payload=payload, request=mock_request, db=mock_db, current_user=mock_user)

    assert res.status == "succeeded"
    assert res.id == intent_id

@pytest.mark.asyncio
async def test_confirm_subscription_deducts_balance(mock_fastapi_dependency):
    import routers.deposit as deposit_router
    from schemas.deposit_mock import PaymentIntentConfirm

    mock_db = MagicMock()
    mock_db.execute = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.add = MagicMock()

    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.is_black = False

    intent_id = f"pi_mock_4900"
    payload = PaymentIntentConfirm(payment_method="pm_mock")

    mock_request = MagicMock()
    mock_request.headers.get.return_value = "idem_sub"

    main_acc = MagicMock()
    main_acc.id = 123
    main_acc.balance = Decimal("100.00")

    call_idx = [0]
    def execute_side_effect(*args, **kwargs):
        idx = call_idx[0]
        call_idx[0] += 1
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        if idx == 0: mock_scalars.first.return_value = None # Idem
        elif idx == 1: mock_scalars.first.return_value = main_acc # Account
        mock_result.scalars.return_value = mock_scalars
        return mock_result

    mock_db.execute.side_effect = execute_side_effect
    fn = getattr(deposit_router.confirm_payment_intent, "__wrapped__", deposit_router.confirm_payment_intent)

    await fn(intent_id=intent_id, payload=payload, request=mock_request, db=mock_db, current_user=mock_user)

    # Verification
    # The router assigns 51.00 directly to the balance attribute.
    # We check if it's the expected value.
    assert main_acc.balance == Decimal("51.00")
    assert mock_user.is_black is True
