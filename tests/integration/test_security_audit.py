import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException, status
import sys
import os

# Set dummy env vars for database initialization during import
os.environ["POSTGRES_USER"] = "test_user"
os.environ["POSTGRES_DB"] = "test_db"
os.environ["POSTGRES_HOST"] = "test_host"
os.environ["POSTGRES_PORT"] = "5432"
os.environ["JWT_SECRET_KEY"] = "test_secret_key"

# Mock the database and other dependencies to avoid needing a real DB/Kafka
@pytest.fixture
def mock_deps(mock_fastapi_dependency, mock_db_dependency):
    return mock_fastapi_dependency

def test_role_checker_admin_only():
    from auth_utils import RoleChecker
    from database import User

    checker = RoleChecker(["admin"])
    admin_user = User(id=1, email="admin@test.com", role="admin")
    regular_user = User(id=2, email="user@test.com", role="user")

    # Should pass
    checker(admin_user)

    # Should fail
    with pytest.raises(HTTPException) as excinfo:
        checker(regular_user)
    assert excinfo.value.status_code == 403

def test_account_ownership_check():
    from services.account_service import get_owned_account
    from models.account import Account
    import asyncio

    db = MagicMock()
    account = Account(id=10, user_id=1, name="My Account")

    async def run_test():
        from unittest.mock import AsyncMock
        res = MagicMock()
        res.scalars().first.return_value = account
        db.execute = AsyncMock(return_value=res)

        result = await get_owned_account(db, 10, 1)
        assert result == account

        # Wrong owner (mock query to return None)
        res.scalars().first.return_value = None
        db.execute = AsyncMock(return_value=res)
        try:
            await get_owned_account(db, 10, 2)
            pytest.fail("Expected exception")
        except HTTPException as e:
            assert e.status_code == 404

    asyncio.run(run_test())

def test_jwt_payload_includes_role():
    from auth_utils import create_access_token
    from jose import jwt
    from auth_utils import SECRET_KEY, ALGORITHM

    token = create_access_token({"sub": "test@test.com", "role": "admin"})
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["role"] == "admin"
    assert payload["sub"] == "test@test.com"

def test_emit_activity_includes_ip_ua():
    from activity import emit_activity
    db = MagicMock()

    with patch('activity.Outbox') as mock_outbox:
        emit_activity(
            db, 1, "security", "login", "Test",
            ip="1.2.3.4", user_agent="Mozilla/5.0"
        )

        # Check that Outbox was called with the correct payload
        args, kwargs = mock_outbox.call_args
        payload = kwargs.get('payload')
        assert payload["ip"] == "1.2.3.4"
        assert payload["user_agent"] == "Mozilla/5.0"
