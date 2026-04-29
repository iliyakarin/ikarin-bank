
import asyncio
import os
import httpx
from config import settings
from turnstile import verify_turnstile

async def test_verification():
    print(f"DEBUG: ENV={settings.ENV}")
    
    # Masking the secret key for security
    secret_key = settings.TURNSTILE_SECRET_KEY or "NOT_CONFIGURED"
    masked_key = f"{secret_key[:4]}...{secret_key[-4:]}" if len(secret_key) > 8 else "****"
    print(f"Testing Turnstile with Secret Key: {masked_key}")

    if secret_key == "1x0000000000000000000000000000000AA":
        print("⚠️ WARNING: Using Cloudflare's 'Always Pass' secret key. This is NOT secure for production.")

    # Use token from environment if available, otherwise use a generic test token
    # Cloudflare's 'Always Pass' secret key will accept ANY non-empty token.
    token = os.getenv("TURNSTILE_VERIFY_TOKEN", "test-token-only")

    if not os.getenv("TURNSTILE_VERIFY_TOKEN"):
        print("ℹ️ No TURNSTILE_VERIFY_TOKEN environment variable found, using default test token.")

    # We'll use the actual backend function but with extra logging if it fails
    try:
        result = await verify_turnstile(token)
    except Exception as e:
        print(f"Exception: {e}")
        result = False
    print(f"Verification Result: {result}")
    
    if result:
        print("✅ Backend Turnstile verification is working with Test Keys.")
    else:
        print("❌ Backend Turnstile verification failed.")

    # Check for Deposit Mock settings
    print(f"Deposit Mock URL: {settings.DEPOSIT_MOCK_URL}")
    print(f"Deposit Mock API Key set: {bool(settings.DEPOSIT_MOCK_API_KEY)}")
    if settings.DEPOSIT_MOCK_URL == "http://deposit-funds-mock:8000" and settings.DEPOSIT_MOCK_API_KEY:
        print("✅ Deposit Mock settings are correctly configured.")
    else:
        print("❌ Deposit Mock settings mismatch.")

if __name__ == "__main__":
    asyncio.run(test_verification())
