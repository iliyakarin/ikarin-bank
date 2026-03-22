import pytest
import sys
import os
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timezone
from fastapi import HTTPException, status

# Add the backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

@pytest.fixture(scope="session", autouse=True)
def set_env():
    os.environ["ENV"] = "test"
    os.environ["JWT_SECRET_KEY"] = "test_secret_key"
    os.environ["JWT_ALGORITHM"] = "HS256"
    os.environ["POSTGRES_USER"] = "postgres"
    os.environ["POSTGRES_PASSWORD"] = "postgres"
    os.environ["POSTGRES_DB"] = "karin_bank_test"
    os.environ["POSTGRES_HOST"] = "localhost"
    os.environ["POSTGRES_PORT"] = "5432"
    os.environ["ACCOUNT_ENCRYPTION_KEY"] = "SktDOUhNb09UT1R6TzI1T0Z3Y0l4Z0l3S3NId0t6azQ="
    os.environ["KAFKA_BOOTSTRAP_SERVERS"] = "localhost:9092"
    os.environ["CLICKHOUSE_HOST"] = "localhost"
    os.environ["SIMULATOR_URL"] = "http://simulator:8001"
    os.environ["SIMULATOR_API_KEY"] = "test_api_key"

@pytest.fixture
def mock_db_dependency():
    mock_db = AsyncMock()
    # Mock result for queries
    res = MagicMock()
    res.scalars().all.return_value = []
    res.scalars().first.return_value = None
    res.scalar.return_value = None
    mock_db.execute.return_value = res
    mock_db.commit.return_value = None
    mock_db.rollback.return_value = None
    
    async def mock_get_db():
        yield mock_db

    # Patch SessionLocal to return the mock_db when used as a context manager
    mock_session_factory = MagicMock()
    mock_session_factory.return_value.__aenter__.return_value = mock_db
    mock_session_factory.return_value.__aexit__.return_value = None

    with patch("auth_utils.get_db", side_effect=mock_get_db), \
         patch("database.SessionLocal", mock_session_factory):
        yield mock_db

@pytest.fixture
def mock_fastapi_dependency():
    mock_fastapi = MagicMock()
    mock_fastapi.HTTPException = HTTPException
    mock_fastapi.status = status
    
    def mock_decorator(path, **kwargs):
        def wrapper(func):
            return func
        return wrapper

    mock_router = MagicMock()
    mock_router.get.side_effect = mock_decorator
    mock_router.post.side_effect = mock_decorator
    mock_router.put.side_effect = mock_decorator
    mock_router.patch.side_effect = mock_decorator
    mock_router.delete.side_effect = mock_decorator
    
    mock_fastapi.APIRouter.return_value = mock_router
    
    mock_main = MagicMock()
    mock_main.app = MagicMock()
    mock_main.HTTPException = HTTPException
    mock_main.status = status

    # We only patch external things that shouldn't run logic
    modules_to_patch = {
        "fastapi": mock_fastapi,
        "fastapi.security": MagicMock(),
        "aiokafka": MagicMock(),
        "clickhouse_connect": MagicMock(),
    }

    with patch.dict(sys.modules, modules_to_patch):
        # Clear cached modules
        to_del = [m for m in sys.modules if m.startswith("backend.routers") or m.startswith("routers.") or 
                  m.startswith("backend.services") or m.startswith("services.") or
                  m.startswith("backend.schemas") or m.startswith("schemas.") or
                  m.startswith("auth_utils") or m.startswith("database") or m.startswith("models.")]
        for m in to_del: del sys.modules[m]
        
        # Reload core modules without standardizing back to backend prefix
        import database
        import auth_utils
        from auth_utils import RoleChecker, create_access_token
        from routers.admin import (
            admin_only, get_stats, list_users, search_user_by_email, delete_user, 
            get_traces, simulate_traffic, get_postgres_logs, get_ch_logs, 
            execute_admin_query, get_banking_metrics, get_kafka_status
        )
        from routers.accounts import (
            create_sub_account, rename_account, internal_transfer, 
            get_account_credentials, get_account_balance
        )
        from routers.transfers import (
            create_p2p_transfer, create_transfer, create_payment_request,
            get_payment_requests, decline_payment_request, get_scheduled_payments
        )
        from routers.deposit import (
            create_checkout_session, create_payment_intent, create_payment_method,
            confirm_payment_intent, create_portal_session, deposit_webhook,
            cancel_subscription, get_my_subscription,
            handle_checkout_completed, handle_subscription_deleted
        )
        
        mock_main.RoleChecker = RoleChecker
        mock_main.create_access_token = create_access_token
        mock_main.admin_only = admin_only
        mock_main.get_stats = get_stats
        mock_main.list_users = list_users
        mock_main.search_user_by_email = search_user_by_email
        mock_main.delete_user = delete_user
        mock_main.get_traces = get_traces
        mock_main.simulate_traffic = simulate_traffic
        mock_main.get_postgres_logs = get_postgres_logs
        mock_main.get_ch_logs = get_ch_logs
        mock_main.execute_admin_query = execute_admin_query
        mock_main.get_banking_metrics = get_banking_metrics
        mock_main.get_kafka_status = get_kafka_status
        mock_main.create_sub_account = create_sub_account
        mock_main.rename_account = rename_account
        mock_main.internal_transfer = internal_transfer
        mock_main.get_account_credentials = get_account_credentials
        mock_main.get_account_balance = get_account_balance
        mock_main.create_p2p_transfer = create_p2p_transfer
        mock_main.create_transfer = create_transfer
        mock_main.create_payment_request = create_payment_request
        mock_main.get_payment_requests = get_payment_requests
        mock_main.decline_payment_request = decline_payment_request
        mock_main.get_scheduled_payments = get_scheduled_payments
        mock_main.create_checkout_session = create_checkout_session
        mock_main.create_payment_intent = create_payment_intent
        mock_main.create_payment_method = create_payment_method
        mock_main.confirm_payment_intent = confirm_payment_intent
        mock_main.create_portal_session = create_portal_session
        mock_main.deposit_webhook = deposit_webhook
        mock_main.cancel_subscription = cancel_subscription
        mock_main.get_my_subscription = get_my_subscription
        mock_main.handle_checkout_completed = handle_checkout_completed
        mock_main.handle_subscription_deleted = handle_subscription_deleted
        
        # Schemas
        from schemas.transfers import P2PTransferRequest
        mock_main.P2PTransferRequest = P2PTransferRequest
        
        yield mock_main

@pytest.fixture(autouse=True)
def use_real_fastapi():
    yield

async def create_test_user(db, email: str, balance: int = 10000):
    from database import User, Account
    from auth_utils import create_access_token
    user = User(first_name="Test", last_name="User", email=email, password_hash="hash")
    db.add(user)
    await db.flush()
    account = Account(user_id=user.id, is_main=True, balance=balance, account_number_last_4="1234")
    db.add(account)
    await db.flush()
    token = create_access_token({"sub": email})
    return user, account, token

async def create_admin_user(db, email: str):
    from database import User
    from auth_utils import create_access_token
    user = User(first_name="Admin", last_name="User", email=email, password_hash="hash", role="admin")
    db.add(user)
    await db.flush()
    token = create_access_token({"sub": email})
    return user, token
