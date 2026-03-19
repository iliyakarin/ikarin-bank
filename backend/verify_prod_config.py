
import asyncio
import os
import httpx
from config import settings
from turnstile import verify_turnstile

async def test_verification():
    print(f"DEBUG: ENV={settings.ENV}")
    print(f"Testing Turnstile with Secret Key: {settings.TURNSTILE_SECRET_KEY}")
    
    # Cloudflare's 'Always Pass' secret key will accept ANY non-empty token.
    token = "0.always-pass-token"
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
