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
os.environ["SECRET_KEY"] = "test_secret_key"

# Mock the database and other dependencies to avoid needing a real DB/Kafka
@pytest.fixture
def mock_deps(mock_fastapi_dependency, mock_db_dependency):
    return mock_fastapi_dependency

def test_role_checker_admin_only():
    from main import RoleChecker, User
    
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
    from routers.accounts import check_account_owner
    from database import Account
    
    db = MagicMock()
    # Mocking the query
    account = Account(id=10, user_id=1, name="My Account")
    db.query().filter().first.return_value = account
    
    # Correct owner
    result = check_account_owner(10, 1, db)
    assert result == account
    
    # Wrong owner (mock query to return None)
    db.query().filter().first.return_value = None
    with pytest.raises(HTTPException) as excinfo:
        check_account_owner(10, 2, db)
    assert excinfo.value.status_code == 404

def test_jwt_payload_includes_role():
    from main import create_access_token
    import jwt
    from main import SECRET_KEY, ALGORITHM
    
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
