import pytest
from unittest.mock import patch, AsyncMock
from turnstile import verify_turnstile
from config import settings

@pytest.mark.asyncio
async def test_verify_turnstile_non_production():
    # Mock settings.ENV to something other than "production"
    with patch("turnstile.settings") as mock_settings:
        mock_settings.ENV = "development"
        result = await verify_turnstile("some-token")
        assert result is True

@pytest.mark.asyncio
async def test_verify_turnstile_missing_token_production():
    with patch("turnstile.settings") as mock_settings:
        mock_settings.ENV = "production"
        result = await verify_turnstile("")
        assert result is False

@pytest.mark.asyncio
async def test_verify_turnstile_success_production():
    with patch("turnstile.settings") as mock_settings:
        mock_settings.ENV = "production"
        mock_settings.TURNSTILE_SECRET_KEY = "secret-key"
        
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.return_value = AsyncMock()
            mock_post.return_value.status_code = 200
            mock_post.return_value.json = lambda: {"success": True}
            
            result = await verify_turnstile("valid-token")
            assert result is True
            mock_post.assert_called_once()

@pytest.mark.asyncio
async def test_verify_turnstile_failure_production():
    with patch("turnstile.settings") as mock_settings:
        mock_settings.ENV = "production"
        mock_settings.TURNSTILE_SECRET_KEY = "secret-key"
        
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.return_value = AsyncMock()
            mock_post.return_value.status_code = 200
            mock_post.return_value.json = lambda: {"success": False, "error-codes": ["invalid-input-response"]}
            
            result = await verify_turnstile("invalid-token")
            assert result is False

@pytest.mark.asyncio
async def test_verify_turnstile_api_error_production():
    with patch("turnstile.settings") as mock_settings:
        mock_settings.ENV = "production"
        mock_settings.TURNSTILE_SECRET_KEY = "secret-key"
        
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.side_effect = Exception("API Down")
            
            result = await verify_turnstile("any-token")
            assert result is False
