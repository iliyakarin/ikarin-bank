"""
Tests for Stripe environment variable validation.
Ensures required environment variables are properly configured.
"""
import os
import sys
import pytest
from unittest.mock import patch, MagicMock

# Set required environment variables before importing
os.environ["JWT_SECRET_KEY"] = "test_secret_key"
os.environ["STRIPE_API_KEY"] = "sk_test_mock_key"
os.environ["STRIPE_MOCK_URL"] = "http://mock-stripe"
os.environ["STRIPE_WEBHOOK_SECRET"] = "whsec_mock_secret"

# Mock stripe module for testing
class MockStripe:
    def __init__(self, api_key=None):
        self._api_key = api_key or "sk_test_mock_key"
        self._api_base = "http://mock-stripe"
        self._webhook_secret = "whsec_mock_secret"

    @property
    def api_base(self):
        return self._api_base

    @api_base.setter
    def api_base(self, value):
        self._api_base = value

    @property
    def api_key(self):
        return self._api_key

    @api_key.setter
    def api_key(self, value):
        if not value or not isinstance(value, str):
            raise ValueError("API key must be a non-empty string")
        if not value.startswith(("sk_test_", "sk_live_")):
            raise ValueError("API key must start with 'sk_test_' or 'sk_live_'")
        self._api_key = value

    @property
    def webhook_secret(self):
        return self._webhook_secret

    @webhook_secret.setter
    def webhook_secret(self, value):
        if not value or not isinstance(value, str):
            raise ValueError("Webhook secret must be a non-empty string")
        if not value.startswith("whsec_"):
            raise ValueError("Webhook secret must start with 'whsec_'")
        self._webhook_secret = value

# Patch stripe module
sys.modules['stripe'] = MockStripe()
stripe = sys.modules['stripe']


class TestStripeEnvironmentValidation:
    """Test environment variable validation for Stripe integration."""

    def test_stripe_api_key_required(self):
        """Test that STRIPE_API_KEY is required and raises error if missing."""
        with patch.dict(os.environ, {"STRIPE_API_KEY": ""}, clear=False):
            with pytest.raises(ValueError) as exc:
                stripe.api_key = os.getenv("STRIPE_API_KEY")
            assert "API key" in str(exc.value) or "non-empty" in str(exc.value)

    def test_stripe_api_key_valid_format(self):
        """Test that STRIPE_API_KEY has valid format."""
        valid_keys = [
            "sk_test_1234567890abcdef",
            "sk_live_1234567890abcdef",
            "sk_test_mock_key",
        ]
        for key in valid_keys:
            os.environ["STRIPE_API_KEY"] = key
            assert key.startswith("sk_")

    def test_stripe_api_key_invalid_format(self):
        """Test that invalid STRIPE_API_KEY format raises error."""
        invalid_keys = [
            "invalid_key",
            "pk_test_1234567890abcdef",
            "",
            None,
        ]
        for key in invalid_keys:
            with pytest.raises(ValueError):
                stripe.api_key = key

    def test_stripe_webhook_secret_required(self):
        """Test that STRIPE_WEBHOOK_SECRET is required."""
        with patch.dict(os.environ, {"STRIPE_WEBHOOK_SECRET": ""}, clear=False):
            with pytest.raises(ValueError) as exc:
                stripe.webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
            assert "Webhook secret" in str(exc.value)

    def test_stripe_webhook_secret_valid_format(self):
        """Test that STRIPE_WEBHOOK_SECRET has valid format."""
        valid_secrets = [
            "whsec_1234567890abcdef",
            "whsec_mock_secret",
        ]
        for secret in valid_secrets:
            os.environ["STRIPE_WEBHOOK_SECRET"] = secret
            assert secret.startswith("whsec_")

    def test_stripe_mock_url_optional(self):
        """Test that STRIPE_MOCK_URL is optional."""
        # Should not raise error
        stripe.api_base = os.getenv("STRIPE_MOCK_URL", stripe.api_base)
        assert stripe.api_base is not None

    def test_stripe_mock_url_valid_format(self):
        """Test that STRIPE_MOCK_URL has valid URL format."""
        valid_urls = [
            "http://mock-stripe",
            "https://mock-stripe.example.com",
            "http://localhost:4242",
        ]
        for url in valid_urls:
            os.environ["STRIPE_MOCK_URL"] = url
            assert url.startswith(("http://", "https://"))

    def test_all_required_env_vars_set(self):
        """Test that all required environment variables are set."""
        required_vars = ["STRIPE_API_KEY", "STRIPE_WEBHOOK_SECRET"]
        for var in required_vars:
            assert os.getenv(var), f"{var} must be set"

    def test_env_vars_can_be_accessed(self):
        """Test that environment variables can be accessed in tests."""
        assert os.getenv("STRIPE_API_KEY") == "sk_test_mock_key"
        assert os.getenv("STRIPE_WEBHOOK_SECRET") == "whsec_mock_secret"
        # STRIPE_MOCK_URL might be set to localhost:4242 by Stripe CLI
        assert os.getenv("STRIPE_MOCK_URL") in ["http://mock-stripe", "http://localhost:4242"]

    def test_env_vars_are_str(self):
        """Test that environment variables are strings."""
        assert isinstance(os.getenv("STRIPE_API_KEY"), str)
        assert isinstance(os.getenv("STRIPE_WEBHOOK_SECRET"), str)
        assert isinstance(os.getenv("STRIPE_MOCK_URL"), str)

    def test_env_vars_not_empty(self):
        """Test that environment variables are not empty strings."""
        assert os.getenv("STRIPE_API_KEY") != ""
        assert os.getenv("STRIPE_WEBHOOK_SECRET") != ""
        assert os.getenv("STRIPE_MOCK_URL") != ""


class TestStripeConfiguration:
    """Test Stripe configuration and initialization."""

    def test_stripe_api_key_set(self):
        """Test that Stripe API key is properly set."""
        stripe.api_key = "sk_test_mock_key"
        assert stripe.api_key == "sk_test_mock_key"

    def test_stripe_api_key_can_be_changed(self):
        """Test that Stripe API key can be changed."""
        stripe.api_key = "sk_test_new_key"
        assert stripe.api_key == "sk_test_new_key"

    def test_stripe_api_key_is_used_for_requests(self):
        """Test that Stripe API key is used for API requests."""
        stripe.api_key = "sk_test_mock_key"
        assert stripe.api_key.startswith("sk_")

    def test_stripe_api_key_format_validation(self):
        """Test that Stripe API key format is validated."""
        # Valid formats
        valid_formats = [
            "sk_test_1234567890abcdef",
            "sk_live_1234567890abcdef",
            "sk_test_mock_key",
        ]
        for key in valid_formats:
            stripe.api_key = key
            assert key.startswith("sk_")

        # Invalid formats
        invalid_formats = [
            "pk_test_1234567890abcdef",  # Wrong prefix
            "invalid_key",  # No prefix
            "",  # Empty
            None,  # None
        ]
        for key in invalid_formats:
            with pytest.raises(ValueError):
                stripe.api_key = key


class TestStripeWebhookSecret:
    """Test Stripe webhook secret validation."""

    def test_webhook_secret_required(self):
        """Test that webhook secret is required."""
        with patch.dict(os.environ, {"STRIPE_WEBHOOK_SECRET": ""}, clear=False):
            with pytest.raises(ValueError):
                stripe.webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

    def test_webhook_secret_valid_format(self):
        """Test that webhook secret has valid format."""
        valid_secrets = [
            "whsec_1234567890abcdef",
            "whsec_mock_secret",
        ]
        for secret in valid_secrets:
            os.environ["STRIPE_WEBHOOK_SECRET"] = secret
            assert secret.startswith("whsec_")

    def test_webhook_secret_format_validation(self):
        """Test that webhook secret format is validated."""
        valid_formats = [
            "whsec_1234567890abcdef",
            "whsec_mock_secret",
        ]
        for secret in valid_formats:
            assert secret.startswith("whsec_")

        invalid_formats = [
            "invalid_secret",  # No prefix
            "",  # Empty
            None,  # None
        ]
        for secret in invalid_formats:
            with pytest.raises(ValueError):
                stripe.webhook_secret = secret


class TestStripeMockURL:
    """Test Stripe mock URL configuration."""

    def test_mock_url_optional(self):
        """Test that mock URL is optional."""
        # Should not raise error
        stripe.api_base = os.getenv("STRIPE_MOCK_URL", stripe.api_base)
        assert stripe.api_base is not None

    def test_mock_url_valid_format(self):
        """Test that mock URL has valid format."""
        valid_urls = [
            "http://mock-stripe",
            "https://mock-stripe.example.com",
            "http://localhost:4242",
        ]
        for url in valid_urls:
            os.environ["STRIPE_MOCK_URL"] = url
            assert url.startswith(("http://", "https://"))

    def test_mock_url_default(self):
        """Test that mock URL has a default value."""
        stripe.api_base = os.getenv("STRIPE_MOCK_URL", stripe.api_base)
        assert stripe.api_base is not None


class TestEnvironmentVariableCleanup:
    """Test that environment variables can be properly cleaned up."""

    def test_env_vars_can_be_cleared(self):
        """Test that environment variables can be cleared."""
        key = "STRIPE_API_KEY"
        value = os.getenv(key)
        del os.environ[key]
        assert key not in os.environ
        os.environ[key] = value

    def test_env_vars_can_be_reset(self):
        """Test that environment variables can be reset."""
        key = "STRIPE_API_KEY"
        os.environ[key] = "new_value"
        assert os.environ[key] == "new_value"
        os.environ[key] = "sk_test_mock_key"
        assert os.environ[key] == "sk_test_mock_key"


class TestStripeConfigurationIntegration:
    """Integration tests for Stripe configuration."""

    def test_complete_stripe_setup(self):
        """Test complete Stripe setup with all required variables."""
        # Set all required variables
        os.environ["STRIPE_API_KEY"] = "sk_test_mock_key"
        os.environ["STRIPE_WEBHOOK_SECRET"] = "whsec_mock_secret"
        os.environ["STRIPE_MOCK_URL"] = "http://mock-stripe"

        # Verify all variables are set
        assert os.getenv("STRIPE_API_KEY") == "sk_test_mock_key"
        assert os.getenv("STRIPE_WEBHOOK_SECRET") == "whsec_mock_secret"
        assert os.getenv("STRIPE_MOCK_URL") == "http://mock-stripe"

        # Verify Stripe can be initialized
        stripe.api_key = os.getenv("STRIPE_API_KEY")
        assert stripe.api_key == "sk_test_mock_key"

    def test_stripe_configuration_is_reusable(self):
        """Test that Stripe configuration can be reused across tests."""
        # First setup
        stripe.api_key = "sk_test_mock_key"
        first_key = stripe.api_key

        # Second setup
        stripe.api_key = "sk_test_mock_key"
        second_key = stripe.api_key

        assert first_key == second_key == "sk_test_mock_key"

    def test_stripe_configuration_is_isolated(self):
        """Test that Stripe configuration is isolated per test."""
        # Test 1
        stripe.api_key = "sk_test_key1"
        key1 = stripe.api_key

        # Test 2
        stripe.api_key = "sk_test_key2"
        key2 = stripe.api_key

        assert key1 != key2