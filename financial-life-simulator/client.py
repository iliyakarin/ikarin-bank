"""Thin async client for the karin-bank API.

Authenticates as a trusted internal service: presents a shared secret header
(X-Service-Key) that lets /auth/login and /auth/register bypass the Turnstile
captcha check (see backend/routers/auth.py::_is_trusted_service). All money
movement still goes through the real API, so ownership checks, idempotency,
and the outbox/ClickHouse pipeline all fire exactly as they would for a human
user.
"""
import logging
from typing import Optional, List, Dict, Any
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
            "/v1/login",
            data={"username": email, "password": password},
            headers=SERVICE_HEADERS,
        )
        resp.raise_for_status()
        return resp.json()["access_token"]

    async def register(self, email: str, password: str, first_name: str, last_name: str) -> None:
        resp = await self._http.post(
            "/v1/register",
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
            logger.info("Account %s login failed (401), attempting to register", email)
            try:
                await self.register(email, password, first_name, last_name)
                return await self.login(email, password)
            except httpx.HTTPStatusError as reg_err:
                if reg_err.response.status_code == 400 and "already registered" in reg_err.response.text:
                    fallback_email = f"sim_{email}"
                    logger.warning("Account %s exists with different password, attempting fallback %s", email, fallback_email)
                    return await self.ensure_logged_in(fallback_email, password, first_name, last_name)
                raise

    async def get_accounts(self, token: str) -> List[Dict[str, Any]]:
        resp = await self._http.get("/v1/accounts", headers=_auth(token))
        resp.raise_for_status()
        return resp.json().get("accounts", [])

    async def get_main_account_info(self, token: str) -> Dict[str, Any]:
        accounts = await self.get_accounts(token)
        main = next((a for a in accounts if a.get("is_main")), accounts[0])
        return main

    async def ensure_savings_account(self, token: str, name: str = "High Yield Savings") -> Dict[str, Any]:
        accounts = await self.get_accounts(token)
        savings = next((a for a in accounts if a.get("name", "").lower() == name.lower() or "saving" in a.get("name", "").lower()), None)
        if savings:
            return savings
        try:
            resp = await self._http.post(
                "/v1/accounts/sub",
                json={"name": name},
                headers=_auth(token),
            )
            resp.raise_for_status()
            return resp.json()
        except Exception:
            logger.exception("Failed to create savings account %s", name)
            accounts = await self.get_accounts(token)
            return accounts[0]

    async def internal_transfer(
        self, token: str, from_account_id: int, to_account_id: int, amount: int, commentary: str, idempotency_key: str
    ) -> Dict[str, Any]:
        resp = await self._http.post(
            "/v1/accounts/transfer/internal",
            json={
                "from_account_id": from_account_id,
                "to_account_id": to_account_id,
                "amount": amount,
                "commentary": commentary,
                "idempotency_key": idempotency_key,
            },
            headers=_auth(token),
        )
        resp.raise_for_status()
        return resp.json()

    async def create_card_deposit(self, token: str, amount: int, idempotency_key: str) -> Dict[str, Any]:
        """Simulates an external card deposit via Payment Intent + Confirm."""
        pi_resp = await self._http.post(
            "/v1/payment_intents",
            json={"amount": amount, "currency": "usd", "metadata": {"source": "simulator_card_deposit"}},
            headers=_auth(token),
        )
        pi_resp.raise_for_status()
        intent = pi_resp.json()
        intent_id = intent["id"]

        confirm_resp = await self._http.post(
            f"/v1/payment_intents/{intent_id}/confirm",
            json={"payment_method": "pm_card_visa"},
            headers={**_auth(token), "Idempotency-Key": idempotency_key},
        )
        confirm_resp.raise_for_status()
        return confirm_resp.json()

    async def expense(
        self, token: str, account_id: int, amount: int, category: str, merchant: str, idempotency_key: str
    ) -> Dict[str, Any]:
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
        self, token: str, recipient_email: str, amount: int, commentary: str, idempotency_key: str,
        subscriber_id: Optional[str] = None, payment_request_id: Optional[int] = None
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "recipient_email": recipient_email,
            "amount": amount,
            "commentary": commentary,
            "idempotency_key": idempotency_key,
        }
        if subscriber_id:
            payload["subscriber_id"] = subscriber_id
        if payment_request_id:
            payload["payment_request_id"] = payment_request_id

        resp = await self._http.post(
            "/v1/p2p-transfer",
            json=payload,
            headers=_auth(token),
        )
        resp.raise_for_status()
        return resp.json()

    async def admin_credit(
        self, token: str, recipient_email: str, amount: int, category: str,
        source_name: str, commentary: str, idempotency_key: str,
    ) -> Dict[str, Any]:
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

    async def get_contacts(self, token: str) -> List[Dict[str, Any]]:
        resp = await self._http.get("/v1/contacts", headers=_auth(token))
        resp.raise_for_status()
        return resp.json()

    async def ensure_contact(self, token: str, name: str, email: str, contact_type: str = "karin") -> Dict[str, Any]:
        contacts = await self.get_contacts(token)
        for c in contacts:
            if c.get("contact_email", "").lower() == email.lower():
                return c
        try:
            resp = await self._http.post(
                "/v1/contacts",
                json={"contact_name": name, "contact_email": email, "contact_type": contact_type},
                headers=_auth(token),
            )
            resp.raise_for_status()
            return resp.json()
        except Exception:
            logger.warning("Could not add contact %s (%s)", name, email)
            return {}

    async def create_payment_request(self, token: str, target_email: str, amount: int, purpose: str) -> Dict[str, Any]:
        resp = await self._http.post(
            "/v1/requests/create",
            json={"target_email": target_email, "amount": amount, "purpose": purpose},
            headers=_auth(token),
        )
        resp.raise_for_status()
        return resp.json()

    async def get_payment_requests(self, token: str) -> List[Dict[str, Any]]:
        resp = await self._http.get("/v1/requests", headers=_auth(token))
        resp.raise_for_status()
        return resp.json()

    async def decline_payment_request(self, token: str, request_id: int) -> Dict[str, Any]:
        resp = await self._http.post(
            f"/v1/requests/{request_id}/decline",
            headers=_auth(token),
        )
        resp.raise_for_status()
        return resp.json()

    async def wire_transfer(
        self,
        token: str,
        account_id: int,
        amount: int,
        receiver_routing: str,
        receiver_name: str,
        receiver_account: str,
        payment_reference: str,
        idempotency_key: str,
    ) -> Dict[str, Any]:
        resp = await self._http.post(
            "/v1/transfers/wire",
            json={
                "account_id": account_id,
                "amount": amount,
                "receiver_routing": receiver_routing,
                "receiver_name": receiver_name,
                "receiver_account": receiver_account,
                "payment_reference": payment_reference,
                "idempotency_key": idempotency_key,
            },
            headers=_auth(token),
        )
        resp.raise_for_status()
        return resp.json()

    async def fednow_transfer(
        self,
        token: str,
        account_id: int,
        amount: int,
        creditor_routing: str,
        creditor_name: str,
        creditor_account: str,
        remittance_info: str,
        idempotency_key: str,
    ) -> Dict[str, Any]:
        resp = await self._http.post(
            "/v1/transfers/fednow",
            json={
                "account_id": account_id,
                "amount": amount,
                "creditor_routing": creditor_routing,
                "creditor_name": creditor_name,
                "creditor_account": creditor_account,
                "remittance_info": remittance_info,
                "idempotency_key": idempotency_key,
            },
            headers=_auth(token),
        )
        resp.raise_for_status()
        return resp.json()

    async def ach_transfer(
        self,
        token: str,
        account_id: int,
        amount: int,
        receiver_routing: str,
        receiver_name: str,
        receiver_account: str,
        payment_description: str,
        idempotency_key: str,
    ) -> Dict[str, Any]:
        resp = await self._http.post(
            "/v1/transfers/ach",
            json={
                "account_id": account_id,
                "amount": amount,
                "receiver_routing": receiver_routing,
                "receiver_name": receiver_name,
                "receiver_account": receiver_account,
                "payment_description": payment_description,
                "idempotency_key": idempotency_key,
            },
            headers=_auth(token),
        )
        resp.raise_for_status()
        return resp.json()

