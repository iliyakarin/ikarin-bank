import httpx
import logging
from typing import Optional
from config import settings

logger = logging.getLogger(__name__)

async def verify_turnstile(token: str, ip: Optional[str] = None) -> bool:
    """
    Verifies a Cloudflare Turnstile token.
    Skips verification if not in production mode.
    """
    # Skip verification in non-production environments
    if settings.ENV != "production":
        logger.info("Skipping Turnstile verification in non-production environment")
        return True

    if not token:
        logger.warning("Turnstile token missing in production request")
        return False

    if not settings.TURNSTILE_SECRET_KEY:
        logger.error("TURNSTILE_SECRET_KEY not configured in production")
        return False

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "https://challenges.cloudflare.com/turnstile/v0/siteverify",
                data={
                    "secret": settings.TURNSTILE_SECRET_KEY,
                    "response": token,
                    "remoteip": ip
                }
            )
            response.raise_for_status()
            data = response.json()
            success = data.get("success", False)
            
            if not success:
                logger.warning(f"Turnstile verification failed: {data.get('error-codes')}")
            
            return success
    except Exception as e:
        logger.error(f"Error during Turnstile verification: {e}")
        # In case of API error from Cloudflare, we might want to fail closed (False) 
        # for security, or fail open if we don't want to block users during outages.
        # Given this is a bank app, we fail closed.
        return False
