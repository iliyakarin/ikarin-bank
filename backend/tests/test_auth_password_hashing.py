"""Tests for password hashing and authentication error handling resilience."""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from auth_utils import verify_password, get_password_hash, create_access_token
from models.user import User


def test_verify_password_valid():
    """Verify that correct plain password matches its bcrypt hash."""
    plain = "SuperSecurePassword123!"
    hashed = get_password_hash(plain)
    assert verify_password(plain, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_verify_password_corrupted_hash():
    """Verify that corrupted or non-bcrypt hashes do not raise exceptions and return False."""
    plain = "TestPass123!"
    
    # 22-char truncated / non-bcrypt string (like the one seen in production)
    assert verify_password(plain, "b2.fo53277zt5Sy") is False
    
    # Random text
    assert verify_password(plain, "not_a_valid_hash") is False
    
    # Malformed prefix
    assert verify_password(plain, "$invalid$prefix$something") is False
    
    # Empty string or None
    assert verify_password(plain, "") is False
    assert verify_password(plain, None) is False
    assert verify_password("", "some_hash") is False
    assert verify_password(None, "some_hash") is False


@pytest.mark.asyncio
async def test_login_with_corrupted_hash_returns_401_not_500():
    """When a user in DB has a corrupted hash, login must return 401 Unauthorized, not crash with 500."""
    from routers.auth import login
    
    # Mock user with corrupted password_hash
    user = User(
        id=4,
        email="corrupted@example.com",
        password_hash="b2.fo53277zt5Sy",
        role="user"
    )
    
    db = AsyncMock()
    res = MagicMock()
    res.scalars().first.return_value = user
    db.execute.return_value = res
    db.commit.return_value = None
    
    mock_request = MagicMock()
    mock_request.headers.get.return_value = None
    mock_request.client.host = "127.0.0.1"
    
    async def mock_form():
        return {"captcha_token": "dummy"}
    mock_request.form = mock_form
    
    form_data = OAuth2PasswordRequestForm(
        grant_type="password",
        username="corrupted@example.com",
        password="MySecretPassword123!",
        scope="",
        client_id=None,
        client_secret=None
    )
    
    with patch("routers.auth.verify_turnstile", new_callable=AsyncMock) as mock_turnstile:
        mock_turnstile.return_value = True
        
        with pytest.raises(HTTPException) as exc_info:
            await login(request=mock_request, form_data=form_data, db=db)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert exc_info.value.detail == "Incorrect email or password"


@pytest.mark.asyncio
async def test_login_trusted_service_bypass():
    """Trusted service header bypasses turnstile captcha verification."""
    from routers.auth import login
    from config import settings
    
    user = User(
        id=1,
        email="admin@example.com",
        password_hash=get_password_hash("AdminSecret123!"),
        role="admin"
    )
    
    db = AsyncMock()
    res = MagicMock()
    res.scalars().first.return_value = user
    db.execute.return_value = res
    db.commit.return_value = None
    
    mock_request = MagicMock()
    mock_request.headers.get.side_effect = lambda k: settings.SIMULATOR_SERVICE_KEY if k.lower() == "x-service-key" else None
    mock_request.client.host = "127.0.0.1"
    
    async def mock_form():
        return {}
    mock_request.form = mock_form
    
    form_data = OAuth2PasswordRequestForm(
        grant_type="password",
        username="admin@example.com",
        password="AdminSecret123!",
        scope="",
        client_id=None,
        client_secret=None
    )
    
    token_response = await login(request=mock_request, form_data=form_data, db=db)
    assert "access_token" in token_response
    assert token_response["token_type"] == "bearer"
