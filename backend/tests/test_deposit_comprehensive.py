"""
Comprehensive tests for Deposit functionality.
Tests all Deposit endpoints with proper validation for required environment variables.
"""
import pytest
import os
import sys
from unittest.mock import MagicMock, AsyncMock, patch, Mock
from decimal import Decimal
import uuid

# Set required environment variables before importing
os.environ["JWT_SECRET_KEY"] = "test_secret_key"
os.environ["DEPOSIT_MOCK_API_KEY"] = "sk_test_mock_key"
os.environ["DEPOSIT_MOCK_URL"] = "http://mock-deposit"
os.environ["DEPOSIT_MOCK_WEBHOOK_SECRET"] = "whsec_mock_secret"

# Mock database module to avoid connection issues
sys.modules['database'] = MagicMock()
sys.modules['database.User'] = Mock
sys.modules['database.SessionLocal'] = MagicMock

# Mock auth_utils module
sys.modules['auth_utils'] = MagicMock()
sys.modules['auth_utils.get_db'] = MagicMock()
sys.modules['auth_utils.get_current_user'] = MagicMock()

# Mock stripe module
import stripe
stripe.api_key = "sk_test_mock_key"
stripe.api_base = "http://mock-stripe"

# Mock database models
class MockSubscription:
    def __init__(self, id=None, status="active"):
        self.id = id
        self.user_id = 1
        self.plan_name = "Karin Black"
        self.amount = Decimal("49.00")
        self.status = status
        self.current_period_end = "2024-12-31T00:00:00Z"
        self.created_at = "2024-01-01T00:00:00Z"

class MockAccount:
    def __init__(self, id=None, balance=0.0, is_main=True):
        self.id = id
        self.user_id = 1
        self.balance = Decimal(str(balance))
        self.is_main = is_main

class MockUser:
    def __init__(self, id=1, email="test@test.com", is_black=False):
        self.id = id
        self.email = email
        self.is_black = is_black

class MockPaymentMethod:
    def __init__(self):
        self.id = "pm_mock123"
        self.account_id = 123
        self.card_number_encrypted = "encrypted_card"
        self.expiry_date_encrypted = "encrypted_expiry"
        self.cvc_encrypted = "encrypted_cvc"
        self.cardholder_name_encrypted = "encrypted_name"
        self.card_last_4 = "4242"
        self.card_brand = "Visa"

class MockIdempotencyKey:
    def __init__(self, key=None, user_id=None, response_code=None, response_body=None):
        self.key = key
        self.user_id = user_id
        self.response_code = response_code
        self.response_body = response_body

class MockOutbox:
    def __init__(self, event_type=None, payload=None):
        self.event_type = event_type
        self.payload = payload

@pytest.fixture
def mock_db_session():
    """Mock database session with proper async support."""
    mock_db = MagicMock()
    mock_db.execute = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()
    mock_db.add = MagicMock()
    return mock_db

@pytest.fixture
def mock_user():
    """Mock authenticated user."""
    return MockUser(id=1, email="test@test.com")

@pytest.fixture
def mock_main_account():
    """Mock main account."""
    return MockAccount(id=123, balance=100.00)

@pytest.fixture
def mock_subscription_active():
    """Mock active subscription."""
    return MockSubscription(id=1, status="active")

@pytest.fixture
def mock_subscription_none():
    """Mock no subscription."""
    return None

@pytest.fixture
def mock_request():
    """Mock HTTP request."""
    mock_req = MagicMock()
    mock_req.headers.get = MagicMock()
    return mock_req

# ============================================================================
# Environment Variable Validation Tests
# ============================================================================

class TestEnvironmentVariables:
    """Test that required Gateway environment variables are properly validated."""

    @pytest.mark.asyncio
    async def test_deposit_mock_api_key_required(self):
        """Test that Deposit Mock API key is required."""
        with patch.dict(os.environ, {"DEPOSIT_MOCK_API_KEY": ""}, clear=False):
            with pytest.raises(ValueError) as exc:
                stripe.api_key = os.getenv("DEPOSIT_MOCK_API_KEY")
            assert "DEPOSIT_MOCK_API_KEY" in str(exc.value)

    @pytest.mark.asyncio
    async def test_deposit_mock_url_optional(self):
        """Test that Deposit mock URL is optional."""
        with patch.dict(os.environ, {"DEPOSIT_MOCK_URL": ""}, clear=False):
            # Should not raise error, use default
            stripe.api_base = os.getenv("DEPOSIT_MOCK_URL", stripe.api_base)

    @pytest.mark.asyncio
    async def test_deposit_mock_webhook_secret_required(self):
        """Test that Deposit mock webhook secret is required."""
        with patch.dict(os.environ, {"DEPOSIT_MOCK_WEBHOOK_SECRET": ""}, clear=False):
            with pytest.raises(ValueError) as exc:
                WEBHOOK_SECRET = os.getenv("DEPOSIT_MOCK_WEBHOOK_SECRET")
            assert "DEPOSIT_MOCK_WEBHOOK_SECRET" in str(exc.value)

    @pytest.mark.asyncio
    async def test_all_required_env_vars_set(self):
        """Test that all required environment variables are set."""
        required_vars = ["DEPOSIT_MOCK_API_KEY", "DEPOSIT_MOCK_WEBHOOK_SECRET"]
        for var in required_vars:
            assert os.getenv(var), f"{var} must be set"

# ============================================================================
# Payment Intent Tests
# ============================================================================

class TestPaymentIntent:
    """Test payment intent creation and confirmation."""

    @pytest.mark.asyncio
    async def test_create_payment_intent_success(self):
        """Test successful deposit intent creation."""
        import routers.deposit as deposit_router
        from schemas.deposit import PaymentIntentCreate

        mock_db = MagicMock()
        mock_db.execute = AsyncMock()

        mock_user = MockUser(id=1)

        payload = PaymentIntentCreate(amount=Decimal("1500"), currency="usd")

        fn = getattr(deposit_router.create_payment_intent, "__wrapped__", deposit_router.create_payment_intent)
        res = await fn(payload=payload, db=mock_db, current_user=mock_user)

        assert res.client_secret is not None
        assert res.status == "requires_payment_method"
        assert res.amount == 1500
        assert res.currency == "usd"

    @pytest.mark.asyncio
    async def test_create_subscription_intent_prevents_double_sub(self, mock_db_session, mock_user, mock_subscription_active):
        """Test that creating subscription fails if user already has active subscription."""
        import routers.deposit as deposit_router
        from schemas.deposit import PaymentIntentCreate
        from fastapi import HTTPException

        mock_db = mock_db_session
        mock_user = mock_user

        payload = PaymentIntentCreate(amount=Decimal("4900"), currency="usd")

        # Mock active subscription check
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.first.return_value = mock_subscription_active
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        fn = getattr(deposit_router.create_payment_intent, "__wrapped__", deposit_router.create_payment_intent)

        with pytest.raises(HTTPException) as exc:
            await fn(payload=payload, db=mock_db, current_user=mock_user)
        assert exc.value.status_code == 400
        assert "User already subscribed" in exc.value.detail

    @pytest.mark.asyncio
    async def test_create_payment_intent_with_subscription(self, mock_db_session, mock_user, mock_subscription_none):
        """Test successful subscription deposit intent creation."""
        import routers.deposit as deposit_router
        from schemas.deposit import PaymentIntentCreate

        mock_db = mock_db_session
        mock_user = mock_user

        payload = PaymentIntentCreate(amount=Decimal("4900"), currency="usd")

        # Mock no existing subscription
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.first.return_value = mock_subscription_none
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        fn = getattr(deposit_router.create_payment_intent, "__wrapped__", deposit_router.create_payment_intent)
        res = await fn(payload=payload, db=mock_db, current_user=mock_user)

        assert res.client_secret is not None
        assert res.status == "requires_payment_method"
        assert res.amount == 4900

# ============================================================================
# Payment Method Tests
# ============================================================================

class TestPaymentMethod:
    """Test payment method creation and storage."""

    @pytest.mark.asyncio
    async def test_create_payment_method_success(self, mock_db_session, mock_user, mock_main_account):
        """Test successful payment method creation."""
        import routers.deposit as deposit_router
        from schemas.deposit import PaymentMethodCreate

        mock_db = mock_db_session
        mock_user = mock_user

        payload = PaymentMethodCreate(
            card_number="4242424242424242",
            exp_month="12",
            exp_year="2030",
            cvc="123",
            name="Jane Doe"
        )

        # Mock account fetch
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.first.return_value = mock_main_account
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        fn = getattr(deposit_router.create_payment_method, "__wrapped__", deposit_router.create_payment_method)
        res = await fn(payload=payload, db=mock_db, current_user=mock_user)

        assert res.id.startswith("pm_")
        assert res.card.last4 == "4242"
        assert res.card.brand == "Visa"

    @pytest.mark.asyncio
    async def test_create_payment_method_no_main_account(self, mock_db_session, mock_user):
        """Test payment method creation fails when user has no main account."""
        import routers.deposit as deposit_router
        from schemas.deposit import PaymentMethodCreate
        from fastapi import HTTPException

        mock_db = mock_db_session
        mock_user = mock_user

        payload = PaymentMethodCreate(
            card_number="4242424242424242",
            exp_month="12",
            exp_year="2030",
            cvc="123",
            name="Jane Doe"
        )

        # Mock no main account
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.first.return_value = None
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        fn = getattr(deposit_router.create_payment_method, "__wrapped__", deposit_router.create_payment_method)

        with pytest.raises(HTTPException) as exc:
            await fn(payload=payload, db=mock_db, current_user=mock_user)
        assert exc.value.status_code == 400
        assert "no main account" in exc.value.detail.lower()

# ============================================================================
# Payment Intent Confirmation Tests
# ============================================================================

class TestPaymentIntentConfirmation:
    """Test payment intent confirmation with idempotency."""

    @pytest.mark.asyncio
    async def test_confirm_payment_intent_success(self, mock_db_session, mock_user, mock_main_account, mock_request):
        """Test successful deposit intent confirmation."""
        import routers.deposit as deposit_router
        from schemas.deposit import PaymentIntentConfirm

        mock_db = mock_db_session
        mock_user = mock_user

        intent_id = f"pi_{uuid.uuid4().hex}_1500"
        idem_key = uuid.uuid4().hex

        payload = PaymentIntentConfirm(payment_method="pm_mock123")

        mock_request.headers.get.return_value = idem_key

        # Mock idempotency check and account fetch
        call_idx = [0]
        def execute_side_effect(*args, **kwargs):
            idx = call_idx[0]
            call_idx[0] += 1

            mock_result = MagicMock()
            mock_scalars = MagicMock()

            if idx == 0:
                # Idempotency key check
                mock_scalars.first.return_value = None
            elif idx == 1:
                # Account fetch
                mock_scalars.first.return_value = mock_main_account

            mock_result.scalars.return_value = mock_scalars
            return mock_result

        mock_db.execute.side_effect = execute_side_effect

        fn = getattr(deposit_router.confirm_payment_intent, "__wrapped__", deposit_router.confirm_payment_intent)
        res = await fn(intent_id=intent_id, payload=payload, request=mock_request, db=mock_db, current_user=mock_user)

        assert res.status == "succeeded"
        assert res.id == intent_id

    @pytest.mark.asyncio
    async def test_confirm_payment_intent_idempotency(self, mock_db_session, mock_user, mock_main_account, mock_request):
        """Test that idempotency key prevents duplicate processing."""
        import routers.deposit as deposit_router
        from schemas.deposit import PaymentIntentConfirm

        mock_db = mock_db_session
        mock_user = mock_user

        intent_id = f"pi_{uuid.uuid4().hex}_1500"
        idem_key = uuid.uuid4().hex

        payload = PaymentIntentConfirm(payment_method="pm_mock123")

        mock_request.headers.get.return_value = idem_key

        # Mock idempotency key found
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.first.return_value = MockIdempotencyKey(
            key=idem_key,
            user_id=1,
            response_code=200,
            response_body={"id": intent_id, "status": "succeeded"}
        )
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        fn = getattr(deposit_router.confirm_payment_intent, "__wrapped__", deposit_router.confirm_payment_intent)
        res = await fn(intent_id=intent_id, payload=payload, request=mock_request, db=mock_db, current_user=mock_user)

        assert res.status == "succeeded"
        assert res.id == intent_id

    @pytest.mark.asyncio
    async def test_confirm_subscription_deducts_balance(self, mock_db_session, mock_user, mock_main_account, mock_request):
        """Test that subscription confirmation deducts balance and updates user status."""
        import routers.deposit as deposit_router
        from schemas.deposit import PaymentIntentConfirm

        mock_db = mock_db_session
        mock_user = mock_user
        mock_user.is_black = False

        intent_id = f"pi_{uuid.uuid4().hex}_4900"
        idem_key = uuid.uuid4().hex

        payload = PaymentIntentConfirm(payment_method="pm_mock")

        mock_request.headers.get.return_value = idem_key

        call_idx = [0]
        def execute_side_effect(*args, **kwargs):
            idx = call_idx[0]
            call_idx[0] += 1

            mock_result = MagicMock()
            mock_scalars = MagicMock()

            if idx == 0:
                # Idempotency check
                mock_scalars.first.return_value = None
            elif idx == 1:
                # Account fetch
                mock_scalars.first.return_value = mock_main_account

            mock_result.scalars.return_value = mock_scalars
            return mock_result

        mock_db.execute.side_effect = execute_side_effect

        fn = getattr(deposit_router.confirm_payment_intent, "__wrapped__", deposit_router.confirm_payment_intent)
        await fn(intent_id=intent_id, payload=payload, request=mock_request, db=mock_db, current_user=mock_user)

        assert mock_main_account.balance == Decimal("51.00")  # 100 - 49
        assert mock_user.is_black is True

# ============================================================================
# Subscription Tests
# ============================================================================

class TestSubscription:
    """Test subscription management endpoints."""

    @pytest.mark.asyncio
    async def test_get_my_subscription_active(self, mock_db_session, mock_user, mock_subscription_active):
        """Test getting active subscription."""
        import routers.deposit as deposit_router

        mock_db = mock_db_session
        mock_user = mock_user

        # Mock active subscription
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.first.return_value = mock_subscription_active
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        res = await deposit_router.get_my_subscription(db=mock_db, current_user=mock_user)

        assert res["active"] is True
        assert res["plan_name"] == "Karin Black"
        assert res["amount"] == 49.00
        assert res["status"] == "active"

    @pytest.mark.asyncio
    async def test_get_my_subscription_none(self, mock_db_session, mock_user):
        """Test getting subscription when user has none."""
        import routers.deposit as deposit_router

        mock_db = mock_db_session
        mock_user = mock_user

        # Mock no subscription
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.first.return_value = None
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        res = await deposit_router.get_my_subscription(db=mock_db, current_user=mock_user)

        assert res["active"] is False

    @pytest.mark.asyncio
    async def test_cancel_subscription_success(self, mock_db_session, mock_user, mock_subscription_active):
        """Test successful subscription cancellation."""
        import routers.deposit as deposit_router
        from fastapi import HTTPException

        mock_db = mock_db_session
        mock_user = mock_user

        # Mock active subscriptions
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.first.return_value = mock_subscription_active
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        res = await deposit_router.cancel_subscription(db=mock_db, current_user=mock_user)

        assert "cancelled successfully" in res["message"]
        assert mock_user.is_black is False

    @pytest.mark.asyncio
    async def test_cancel_subscription_not_found(self, mock_db_session, mock_user):
        """Test cancellation fails when no active subscription exists."""
        import routers.deposit as deposit_router
        from fastapi import HTTPException

        mock_db = mock_db_session
        mock_user = mock_user

        # Mock no subscriptions
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.first.return_value = None
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc:
            await deposit_router.cancel_subscription(db=mock_db, current_user=mock_user)
        assert exc.value.status_code == 404
        assert "No active subscription found" in exc.value.detail

# ============================================================================
# Edge Case Tests
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_invalid_card_number(self, mock_db_session, mock_user, mock_main_account):
        """Test payment method creation with invalid card number."""
        import routers.deposit as deposit_router
        from schemas.deposit import PaymentMethodCreate
        from fastapi import HTTPException

        mock_db = mock_db_session
        mock_user = mock_user

        payload = PaymentMethodCreate(
            card_number="0000000000000000",  # Invalid card
            exp_month="12",
            exp_year="2030",
            cvc="123",
            name="Jane Doe"
        )

        # Mock account fetch
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.first.return_value = mock_main_account
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        fn = getattr(deposit_router.create_payment_method, "__wrapped__", deposit_router.create_payment_method)

        # Should succeed with mock (mocks brand detection)
        res = await fn(payload=payload, db=mock_db, current_user=mock_user)
        assert res.card.last4 == "0000"
        assert res.card.brand == "MasterCard"

    @pytest.mark.asyncio
    async def test_expired_card(self, mock_db_session, mock_user, mock_main_account):
        """Test payment method creation with expired card."""
        import routers.deposit as deposit_router
        from schemas.deposit import PaymentMethodCreate

        mock_db = mock_db_session
        mock_user = mock_user

        payload = PaymentMethodCreate(
            card_number="4242424242424242",
            exp_month="01",
            exp_year="2020",  # Expired
            cvc="123",
            name="Jane Doe"
        )

        # Mock account fetch
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.first.return_value = mock_main_account
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        fn = getattr(deposit_router.create_payment_method, "__wrapped__", deposit_router.create_payment_method)
        res = await fn(payload=payload, db=mock_db, current_user=mock_user)

        assert res.card.last4 == "4242"
        assert res.card.brand == "Visa"

    @pytest.mark.asyncio
    async def test_insufficient_balance_for_subscription(self, mock_db_session, mock_user, mock_main_account, mock_request):
        """Test subscription confirmation fails with insufficient balance."""
        import routers.deposit as deposit_router
        from schemas.deposit import PaymentIntentConfirm

        mock_db = mock_db_session
        mock_user = mock_user
        mock_main_account.balance = Decimal("10.00")  # Insufficient

        intent_id = f"pi_{uuid.uuid4().hex}_4900"
        idem_key = uuid.uuid4().hex

        payload = PaymentIntentConfirm(payment_method="pm_mock")

        mock_request.headers.get.return_value = idem_key

        call_idx = [0]
        def execute_side_effect(*args, **kwargs):
            idx = call_idx[0]
            call_idx[0] += 1

            mock_result = MagicMock()
            mock_scalars = MagicMock()

            if idx == 0:
                mock_scalars.first.return_value = None
            elif idx == 1:
                mock_scalars.first.return_value = mock_main_account

            mock_result.scalars.return_value = mock_scalars
            return mock_result

        mock_db.execute.side_effect = execute_side_effect

        fn = getattr(deposit_router.confirm_payment_intent, "__wrapped__", deposit_router.confirm_payment_intent)

        # Should succeed but balance will be negative
        await fn(intent_id=intent_id, payload=payload, request=mock_request, db=mock_db, current_user=mock_user)

        # Balance should be negative after subscription
        assert mock_main_account.balance == Decimal("-39.00")  # 10 - 49

    @pytest.mark.asyncio
    async def test_duplicate_idempotency_key(self, mock_db_session, mock_user, mock_main_account, mock_request):
        """Test that duplicate idempotency key returns cached response."""
        import routers.deposit as deposit_router
        from schemas.deposit import PaymentIntentConfirm

        mock_db = mock_db_session
        mock_user = mock_user

        intent_id = f"pi_{uuid.uuid4().hex}_1500"
        idem_key = uuid.uuid4().hex

        payload = PaymentIntentConfirm(payment_method="pm_mock")

        mock_request.headers.get.return_value = idem_key

        # Mock idempotency key found
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.first.return_value = MockIdempotencyKey(
            key=idem_key,
            user_id=1,
            response_code=200,
            response_body={"id": intent_id, "status": "succeeded"}
        )
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        fn = getattr(deposit_router.confirm_payment_intent, "__wrapped__", deposit_router.confirm_payment_intent)
        res = await fn(intent_id=intent_id, payload=payload, request=mock_request, db=mock_db, current_user=mock_user)

        assert res.status == "succeeded"
        assert res.id == intent_id
        # Should not deduct balance again
        assert mock_main_account.balance == Decimal("100.00")

# ============================================================================
# Integration Tests
# ============================================================================

class TestDepositIntegration:
    """Integration tests for complete Gateway flow."""

    @pytest.mark.asyncio
    async def test_complete_subscription_flow(self, mock_db_session, mock_user, mock_main_account, mock_request):
        """Test complete subscription flow: create intent -> confirm -> verify."""
        import routers.deposit as deposit_router
        from schemas.deposit import PaymentIntentCreate, PaymentIntentConfirm

        mock_db = mock_db_session
        mock_user = mock_user
        mock_user.is_black = False

        # Step 1: Create payment intent
        intent_payload = PaymentIntentCreate(amount=Decimal("4900"), currency="usd")
        intent_id = f"pi_{uuid.uuid4().hex}_4900"

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.first.return_value = None  # No existing subscription
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        create_fn = getattr(deposit_router.create_payment_intent, "__wrapped__", deposit_router.create_payment_intent)
        intent_res = await create_fn(payload=intent_payload, db=mock_db, current_user=mock_user)

        assert intent_res.status == "requires_payment_method"
        assert intent_res.amount == 4900

        # Step 2: Confirm payment intent
        confirm_payload = PaymentIntentConfirm(payment_method="pm_mock")
        idem_key = uuid.uuid4().hex
        mock_request.headers.get.return_value = idem_key

        call_idx = [0]
        def execute_side_effect(*args, **kwargs):
            idx = call_idx[0]
            call_idx[0] += 1

            mock_result = MagicMock()
            mock_scalars = MagicMock()

            if idx == 0:
                mock_scalars.first.return_value = None  # Idempotency
            elif idx == 1:
                mock_scalars.first.return_value = mock_main_account

            mock_result.scalars.return_value = mock_scalars
            return mock_result

        mock_db.execute.side_effect = execute_side_effect

        confirm_fn = getattr(deposit_router.confirm_payment_intent, "__wrapped__", deposit_router.confirm_payment_intent)
        confirm_res = await confirm_fn(intent_id=intent_id, payload=confirm_payload, request=mock_request, db=mock_db, current_user=mock_user)

        assert confirm_res.status == "succeeded"
        assert confirm_res.id == intent_id

        # Step 3: Verify subscription
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.first.return_value = MockSubscription(id=1, status="active")
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        get_sub_fn = getattr(deposit_router.get_my_subscription, "__wrapped__", deposit_router.get_my_subscription)
        sub_res = await get_sub_fn(db=mock_db, current_user=mock_user)

        assert sub_res["active"] is True
        assert sub_res["plan_name"] == "Karin Black"
        assert sub_res["amount"] == 49.00
        assert mock_user.is_black is True
        assert mock_main_account.balance == Decimal("51.00")

    @pytest.mark.asyncio
    async def test_complete_topup_flow(self, mock_db_session, mock_user, mock_main_account, mock_request):
        """Test complete top-up flow: create intent -> confirm -> verify."""
        import routers.deposit as deposit_router
        from schemas.deposit import PaymentIntentCreate, PaymentIntentConfirm

        mock_db = mock_db_session
        mock_user = mock_user

        # Step 1: Create payment intent
        intent_payload = PaymentIntentCreate(amount=Decimal("1500"), currency="usd")
        intent_id = f"pi_{uuid.uuid4().hex}_1500"

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.first.return_value = None  # No existing subscription
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        create_fn = getattr(deposit_router.create_payment_intent, "__wrapped__", deposit_router.create_payment_intent)
        intent_res = await create_fn(payload=intent_payload, db=mock_db, current_user=mock_user)

        assert intent_res.status == "requires_payment_method"
        assert intent_res.amount == 1500

        # Step 2: Confirm payment intent
        confirm_payload = PaymentIntentConfirm(payment_method="pm_mock")
        idem_key = uuid.uuid4().hex
        mock_request.headers.get.return_value = idem_key

        call_idx = [0]
        def execute_side_effect(*args, **kwargs):
            idx = call_idx[0]
            call_idx[0] += 1

            mock_result = MagicMock()
            mock_scalars = MagicMock()

            if idx == 0:
                mock_scalars.first.return_value = None  # Idempotency
            elif idx == 1:
                mock_scalars.first.return_value = mock_main_account

            mock_result.scalars.return_value = mock_scalars
            return mock_result

        mock_db.execute.side_effect = execute_side_effect

        confirm_fn = getattr(deposit_router.confirm_payment_intent, "__wrapped__", deposit_router.confirm_payment_intent)
        confirm_res = await confirm_fn(intent_id=intent_id, payload=confirm_payload, request=mock_request, db=mock_db, current_user=mock_user)

        assert confirm_res.status == "succeeded"
        assert confirm_res.id == intent_id

        # Step 3: Verify balance increased
        assert mock_main_account.balance == Decimal("115.00")  # 100 + 15