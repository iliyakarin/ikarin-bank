"""Global pytest configuration and environment setup for test execution."""
import os
import sys
from unittest.mock import MagicMock, AsyncMock, patch
import pytest

# Ensure backend and root are on PYTHONPATH
sys.path.insert(0, os.path.abspath("backend"))
sys.path.insert(0, os.path.abspath("."))

# Populate test environment variables before module imports
TEST_ENV = {
    "ENV": "test",
    "JWT_SECRET_KEY": "test_jwt_secret_key_for_testing_suite",
    "JWT_ALGORITHM": "HS256",
    "ACCESS_TOKEN_EXPIRE_MINUTES": "60",
    "CORS_ORIGINS": "http://localhost:3000",
    "ABA_PREFIX": "1234",
    "POSTGRES_USER": "postgres",
    "POSTGRES_PASSWORD": "postgres_test_password",
    "POSTGRES_DB": "karin_bank_test",
    "POSTGRES_HOST": "localhost",
    "POSTGRES_PORT": "5432",
    "ACCOUNT_ENCRYPTION_KEY": "SktDOUhNb09UT1R6TzI1T0Z3Y0l4Z0l3S3NId0t6azQ=",
    "KAFKA_MESSAGE_ENCRYPTION_KEY": "SktDOUhNb09UT1R6TzI1T0Z3Y0l4Z0l3S3NId0t6azQ=",
    "KAFKA_BOOTSTRAP_SERVERS": "localhost:9092",
    "KAFKA_TOPIC": "transactions",
    "KAFKA_ACTIVITY_TOPIC": "activity",
    "KAFKA_CONSUMER_GROUP": "karin-bank",
    "KAFKA_REQUEST_TIMEOUT_MS": "5000",
    "KAFKA_ACKS": "all",
    "KAFKA_RETRY_MAX_RETRIES": "3",
    "KAFKA_RETRY_BACKOFF_MS": "100",
    "KAFKA_DLQ_TOPIC": "transactions-dlq",
    "CLICKHOUSE_HOST": "localhost",
    "CLICKHOUSE_PORT": "8123",
    "CLICKHOUSE_DB": "karin_bank_test",
    "CLICKHOUSE_USER": "default",
    "CLICKHOUSE_PASSWORD": "clickhouse_test_password",
    "DEPOSIT_MOCK_API_KEY": "test_deposit_api_key",
    "DEPOSIT_MOCK_WEBHOOK_SECRET": "test_deposit_webhook_secret",
    "SIMULATOR_URL": "http://localhost:8001",
    "SIMULATOR_API_KEY": "test_simulator_api_key",
    "SIMULATOR_SERVICE_KEY": "test_simulator_service_key",
    "GATEWAY_API_KEY": "test_gateway_api_key",
}

for k, v in TEST_ENV.items():
    os.environ.setdefault(k, v)


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Ensure all test environment variables are set for the session."""
    for k, v in TEST_ENV.items():
        os.environ[k] = v
    yield
