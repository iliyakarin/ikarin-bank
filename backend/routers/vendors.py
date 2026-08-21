from fastapi import APIRouter, Depends, HTTPException, Query
import httpx
import os
import logging
from typing import Optional
from auth_utils import get_current_user
from database import User

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Vendors & Fed Directory"])

from config import settings

FED_GATEWAY_URL = getattr(settings, "MOCK_FED_GATEWAY_URL", "http://mock-fed-gateway:8002")

@router.get("/vendors")
async def get_external_vendors(current_user: User = Depends(get_current_user)):
    """Proxy to get vendors from vendor-simulator."""
    async with httpx.AsyncClient() as client:
        try:
            res = await client.get(f"{settings.SIMULATOR_URL}/vendors", timeout=5.0)
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
            res = await client.get(f"{FED_GATEWAY_URL}/banks", timeout=5.0)
            if res.status_code == 200:
                return res.json()
            return {"banks": []}
        except Exception as e:
            logger.error(f"Error fetching banks: {e}")
            return {"banks": []}

@router.get("/fed/directory/{routing_number}")
async def lookup_routing_number(routing_number: str, current_user: User = Depends(get_current_user)):
    """Lookup ABA routing number in Federal Reserve Directory."""
    async with httpx.AsyncClient() as client:
        try:
            res = await client.get(f"{FED_GATEWAY_URL}/fed/directory/routing/{routing_number}", timeout=5.0)
            if res.status_code == 200:
                return res.json()
            return {"valid": False, "routing_number": routing_number, "errors": ["Lookup failed"]}
        except Exception as e:
            logger.error(f"Error querying Fed directory for routing {routing_number}: {e}")
            return {"valid": False, "routing_number": routing_number, "errors": [str(e)]}

@router.get("/fed/districts")
async def get_fed_districts(current_user: User = Depends(get_current_user)):
    """Retrieve list of 12 Federal Reserve Districts."""
    async with httpx.AsyncClient() as client:
        try:
            res = await client.get(f"{FED_GATEWAY_URL}/fed/districts", timeout=5.0)
            if res.status_code == 200:
                return res.json()
            return []
        except Exception as e:
            logger.error(f"Error fetching Fed districts: {e}")
            return []

@router.get("/fed/institutions")
async def search_fed_institutions(
    q: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    fedwire_only: bool = False,
    fednow_only: bool = False,
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
):
    """Search registered financial institutions in Federal Reserve Directory."""
    params = {"limit": limit}
    if q:
        params["q"] = q
    if state:
        params["state"] = state
    if fedwire_only:
        params["fedwire_only"] = "true"
    if fednow_only:
        params["fednow_only"] = "true"

    async with httpx.AsyncClient() as client:
        try:
            res = await client.get(f"{FED_GATEWAY_URL}/fed/directory/institutions", params=params, timeout=5.0)
            if res.status_code == 200:
                return res.json()
            return {"total": 0, "institutions": []}
        except Exception as e:
            logger.error(f"Error searching Fed institutions: {e}")
            return {"total": 0, "institutions": []}
