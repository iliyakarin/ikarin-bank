import httpx
import logging
from typing import Optional, Any, Dict
from fastapi import HTTPException

logger = logging.getLogger(__name__)

class MockServiceClient:
    """Unified client for interacting with mock services."""

    def __init__(self, base_url: str, api_key: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.headers = {"X-API-Key": api_key} if api_key else {}

    async def _request(
        self, 
        method: str, 
        path: str, 
        data: Optional[Dict[str, Any]] = None, 
        params: Optional[Dict[str, Any]] = None,
        timeout: float = 10.0
    ) -> Dict[str, Any]:
        """Internal helper for making HTTP requests."""
        url = f"{self.base_url}/{path.lstrip('/')}"
        async with httpx.AsyncClient() as client:
            try:
                response = await client.request(
                    method=method,
                    url=url,
                    json=data if method.upper() in ["POST", "PUT", "PATCH"] else None,
                    params=params,
                    headers=self.headers,
                    timeout=timeout
                )
                
                if response.status_code >= 400:
                    logger.error(f"Mock service error: {response.status_code} - {response.text}")
                    raise HTTPException(
                        status_code=response.status_code, 
                        detail=f"Mock service error: {response.text}"
                    )
                
                return response.json()
            except httpx.RequestError as e:
                logger.error(f"HTTP request failed: {e}")
                raise HTTPException(
                    status_code=503, 
                    detail=f"Unable to reach mock service at {self.base_url}"
                )
            except Exception as e:
                logger.error(f"Unexpected error calling mock service: {e}")
                raise HTTPException(status_code=500, detail=str(e))

    async def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return await self._request("GET", path, params=params)

    async def post(self, path: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return await self._request("POST", path, data=data)
