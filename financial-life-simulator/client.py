"""Thin async client for the karin-bank API.

Authenticates as a trusted internal service: presents a shared secret header
(X-Service-Key) that lets /auth/login and /auth/register bypass the Turnstile
captcha check (see backend/routers/auth.py::_is_trusted_service). All money
movement still goes through the real API, so ownership checks, idempotency,
and the outbox/ClickHouse pipeline all fire exactly as they would for a human
user.
"""
import logging
import httpx

from config import settings

logger = logging.getLogger(__name__)

SERVICE_HEADERS = {"X-Service-Key": settings.SIMULATOR_SERVICE_KEY}


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


class ApiClient:
    def __init__(self, base_url: str):
        self._http = httpx.AsyncClient(base_url=base_url, timeout=15.0)

    async def close(self) -> None:
        await self._http.aclose()

    async def login(self, email: str, password: str) -> str:
        resp = await self._http.post(
            "/v1/auth/login",
            data={"username": email, "password": password},
            headers=SERVICE_HEADERS,
        )
        resp.raise_for_status()
        return resp.json()["access_token"]

    async def register(self, email: str, password: str, first_name: str, last_name: str) -> None:
        resp = await self._http.post(
            "/v1/auth/register",
            json={
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "password": password,
            },
            headers=SERVICE_HEADERS,
        )
        if resp.status_code == 400 and "already registered" in resp.text:
            return
        resp.raise_for_status()

    async def ensure_logged_in(self, email: str, password: str, first_name: str, last_name: str) -> str:
        """Logs in; registers the account first if it doesn't exist yet."""
        try:
            return await self.login(email, password)
        except httpx.HTTPStatusError as e:
            if e.response.status_code != 401:
                raise
            logger.info("Account %s not found, registering", email)
            await self.register(email, password, first_name, last_name)
            return await self.login(email, password)

    async def get_main_account_id(self, token: str) -> int:
        resp = await self._http.get("/v1/accounts", headers=_auth(token))
        resp.raise_for_status()
        accounts = resp.json()["accounts"]
        main = next((a for a in accounts if a["is_main"]), accounts[0])
        return main["id"]

    async def expense(
        self, token: str, account_id: int, amount: int, category: str, merchant: str, idempotency_key: str
    ) -> dict:
        resp = await self._http.post(
            "/v1/transfer",
            json={
                "account_id": account_id, "amount": amount, "category": category,
                "merchant": merchant, "idempotency_key": idempotency_key,
            },
            headers=_auth(token),
        )
        resp.raise_for_status()
        return resp.json()

    async def p2p_transfer(
        self, token: str, recipient_email: str, amount: int, commentary: str, idempotency_key: str
    ) -> dict:
        resp = await self._http.post(
            "/v1/p2p-transfer",
            json={
                "recipient_email": recipient_email,
                "amount": amount,
                "commentary": commentary,
                "idempotency_key": idempotency_key,
            },
            headers=_auth(token),
        )
        resp.raise_for_status()
        return resp.json()

    async def admin_credit(
        self, token: str, recipient_email: str, amount: int, category: str,
        source_name: str, commentary: str, idempotency_key: str,
    ) -> dict:
        resp = await self._http.post(
            "/v1/admin/credit",
            json={
                "recipient_email": recipient_email,
                "amount": amount,
                "category": category,
                "source_name": source_name,
                "commentary": commentary,
                "idempotency_key": idempotency_key,
            },
            headers=_auth(token),
        )
        resp.raise_for_status()
        return resp.json()
