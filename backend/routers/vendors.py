from fastapi import APIRouter, Depends, HTTPException
import httpx
import os
import logging
from auth_utils import get_current_user
from database import User

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Vendors"])

from config import settings

@router.get("/vendors")
async def get_external_vendors(current_user: User = Depends(get_current_user)):
    """Proxy to get vendors from vendor-simulator."""
    async with httpx.AsyncClient() as client:
        try:
            res = await client.get("http://vendor-simulator:8001/vendors", timeout=5.0)
            if res.status_code == 200:
                return res.json()
            return {"vendors": []}
        except Exception as e:
            logger.error(f"Error fetching vendors: {e}")
            return {"vendors": []}

@router.get("/banks")
async def get_external_banks(current_user: User = Depends(get_current_user)):
    """Proxy to get banks from mock-fed-gateway."""
    async with httpx.AsyncClient() as client:
        try:
            res = await client.get("http://mock-fed-gateway:8002/banks", timeout=5.0)
            if res.status_code == 200:
                return res.json()
            return {"banks": []}
        except Exception as e:
            logger.error(f"Error fetching banks: {e}")
            return {"banks": []}
        except Exception as e:
            logger.error(f"Error fetching banks: {e}")
            return {"banks": []}

# --- Admin Endpoints ---
