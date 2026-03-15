# Stripe Integration Tests

This directory contains comprehensive tests for the Stripe subscription implementation.

## Test Files

### 1. `test_stripe_comprehensive.py`
Comprehensive tests covering all Stripe endpoints and flows:
- **Payment Intent Tests**: Create, confirm, and manage payment intents
- **Payment Method Tests**: Create and store payment methods
- **Subscription Tests**: Get, create, and cancel subscriptions
- **Edge Case Tests**: Invalid cards, expired cards, insufficient balance
- **Integration Tests**: Complete flows for subscriptions and top-ups

### 2. `test_stripe_env_validation.py`
Tests for environment variable validation:
- Required environment variables (STRIPE_API_KEY, STRIPE_WEBHOOK_SECRET)
- Optional environment variables (STRIPE_MOCK_URL)
- Format validation for API keys and webhook secrets
- Configuration and initialization tests

## Prerequisites

Before running tests, ensure you have:
- Python 3.8+
- Required environment variables set (see `.env.example`)

## Running Tests

### Run All Tests
```bash
cd backend
pytest tests/ -v
```

### Run Specific Test File
```bash
# Comprehensive tests
pytest tests/test_stripe_comprehensive.py -v

# Environment validation tests
pytest tests/test_stripe_env_validation.py -v
```

### Run Specific Test Class
```bash
# Payment intent tests
pytest tests/test_stripe_comprehensive.py::TestPaymentIntent -v

# Environment validation tests
pytest tests/test_stripe_env_validation.py::TestStripeEnvironmentValidation -v
```

### Run Specific Test Method
```bash
pytest tests/test_stripe_comprehensive.py::TestPaymentIntent::test_create_payment_intent_success -v
```

### Run with Coverage
```bash
pytest tests/ --cov=routes.stripe --cov=schemas.stripe_mock --cov-report=html
```

### Run with Verbose Output
```bash
pytest tests/ -v -s
```

## Test Structure

### Mock Objects
The tests use mock objects to simulate database operations and Stripe API responses:

- **MockUser**: Simulates authenticated user
- **MockAccount**: Simulates user account with balance
- **MockSubscription**: Simulates subscription status
- **MockPaymentMethod**: Simulates payment method storage
- **MockIdempotencyKey**: Simulates idempotency key storage
- **MockOutbox**: Simulates event outbox for webhooks

### Test Classes

#### `TestEnvironmentVariables`
Validates that required environment variables are properly configured.

#### `TestPaymentIntent`
Tests payment intent creation and confirmation:
- Successful creation
- Subscription prevention (double subscription check)
- Idempotency handling

#### `TestPaymentMethod`
Tests payment method creation and storage:
- Successful creation
- Missing main account handling

#### `TestPaymentIntentConfirmation`
Tests payment intent confirmation:
- Successful confirmation
- Idempotency key handling
- Balance deduction for subscriptions

#### `TestSubscription`
Tests subscription management:
- Getting active subscription
- Subscription cancellation
- Error handling for missing subscriptions

#### `TestEdgeCases`
Tests edge cases:
- Invalid card numbers
- Expired cards
- Insufficient balance
- Duplicate idempotency keys

#### `TestStripeIntegration`
Integration tests for complete flows:
- Complete subscription flow
- Complete top-up flow

## Environment Variables

### Required
- `STRIPE_API_KEY`: Stripe API key (must start with `sk_test_` or `sk_live_`)
- `STRIPE_WEBHOOK_SECRET`: Webhook secret (must start with `whsec_`)

### Optional
- `STRIPE_MOCK_URL`: Mock Stripe API URL (default: `http://localhost:4242`)

## Example Usage

### Create Payment Intent
```python
payload = PaymentIntentCreate(amount=Decimal("4900"), currency="usd")
res = await create_payment_intent(payload=payload, db=mock_db, current_user=mock_user)
# Returns: PaymentIntent with client_secret and status
```

### Confirm Payment Intent
```python
payload = PaymentIntentConfirm(payment_method="pm_mock")
res = await confirm_payment_intent(
    intent_id="pi_...",
    payload=payload,
    request=mock_request,
    db=mock_db,
    current_user=mock_user
)
# Returns: PaymentIntent with status "succeeded"
```

### Get Subscription
```python
res = await get_my_subscription(db=mock_db, current_user=mock_user)
# Returns: dict with active status, plan details, etc.
```

### Cancel Subscription
```python
res = await cancel_subscription(db=mock_db, current_user=mock_user)
# Returns: dict with cancellation message
```

## Test Coverage

The comprehensive tests aim to cover:
- ✅ All Stripe endpoints
- ✅ Error handling and edge cases
- ✅ Idempotency key handling
- ✅ Balance deduction logic
- ✅ Subscription status management
- ✅ Environment variable validation
- ✅ Complete user flows

## Troubleshooting

### Tests Fail with Missing Environment Variables
Ensure all required environment variables are set:
```bash
export STRIPE_API_KEY="sk_test_..."
export STRIPE_WEBHOOK_SECRET="whsec_..."
```

### Tests Fail with Import Errors
Make sure you're running tests from the `backend/` directory:
```bash
cd backend
pytest tests/ -v
```

### Tests Fail with Mock Errors
Ensure mock objects are properly configured in test fixtures.

## Contributing

When adding new tests:
1. Follow the existing test structure
2. Use mock objects for database operations
3. Test both success and error cases
4. Add comments for complex logic
5. Update this README if adding new test categories