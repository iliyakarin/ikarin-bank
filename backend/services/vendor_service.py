"""Vendor Service.

Single source of truth for fetching vendors from the simulator.
"""
import logging
from config import settings
from services.mock_client import MockServiceClient

logger = logging.getLogger(__name__)

_simulator_client = MockServiceClient(
    base_url=settings.SIMULATOR_URL,
    api_key=getattr(settings, "SIMULATOR_API_KEY", "default-key")
)


async def get_vendors() -> list[dict]:
    """Fetch the vendor list from the vendor simulator."""
    try:
        res = await _simulator_client.get("/vendors")
        return res.get("vendors", [])
    except Exception:
        return []
