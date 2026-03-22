import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch, MagicMock
import sys
import socket

# Mock socket.getaddrinfo to avoid gaierror
original_getaddrinfo = socket.getaddrinfo
def mocked_getaddrinfo(*args, **kwargs):
    if args[0] in ["localhost", "testserver", "127.0.0.1"]:
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('127.0.0.1', args[1]))]
    return original_getaddrinfo(*args, **kwargs)

with patch("socket.getaddrinfo", side_effect=mocked_getaddrinfo):
    # Pre-emptively mock external dependencies
    sys.modules["aiokafka"] = MagicMock()
    
    from main import app
    from database import User, Account
    from auth_utils import get_db

@pytest.mark.asyncio
async def test_register_user_success(mock_db_dependency):
    """
    Test successful user registration with first_name and last_name.
    """
    mock_db = mock_db_dependency
    
    # Mock db.refresh to simulate database setting defaults and ID
    async def mock_refresh(obj):
        if isinstance(obj, User):
            obj.id = 1
            obj.role = "user"
            obj.time_format = "12h"
            obj.date_format = "US"
        elif isinstance(obj, Account):
            obj.id = 1
    
    mock_db.refresh.side_effect = mock_refresh
    
    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    # Also need to mock verify_turnstile and emit_activity
    with patch("routers.auth.verify_turnstile", return_value=AsyncMock(return_value=True)), \
         patch("routers.auth.emit_activity") as mock_emit:
        
        async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
            registration_data = {
                "first_name": "Test",
                "last_name": "User",
                "email": "newuser@example.com",
                "password": "securepassword123",
                "captcha_token": "mock_token"
            }
            response = await ac.post("/v1/register", json=registration_data)
            
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert data["first_name"] == "Test"
    assert data["last_name"] == "User"
    assert data["id"] == 1
    
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_register_user_missing_fields():
    """
    Test that registration fails if first_name or last_name is missing.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        registration_data = {
            "email": "missingfields@example.com",
            "password": "securepassword123",
            "captcha_token": "mock_token"
        }
        response = await ac.post("/v1/register", json=registration_data)
        
    assert response.status_code == 422 # Validation Error
