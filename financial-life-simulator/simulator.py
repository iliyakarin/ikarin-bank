"""Core simulation loop: decides what financial events to fire on each tick.

Access tokens expire in 15 minutes (backend security policy), so every tick
re-authenticates both demo personas rather than caching a token across ticks.
"""
import asyncio
import datetime
import logging
import random
import uuid
from typing import Optional

from client import ApiClient
from config import settings
from state import EventState
from scenarios import (
    random_merchant, random_amount, RENT_MERCHANT, CAR_INSURANCE_MERCHANT,
    SALARY_SOURCE, P2P_MEMOS,
)

logger = logging.getLogger(__name__)


class FinancialLifeSimulator:
    def __init__(self):
        self.client = ApiClient(settings.API_BASE_URL)
        self.state = EventState(settings.STATE_DB_PATH)
        self.last_tick_at: Optional[datetime.datetime] = None
        self._lock = asyncio.Lock()

    async def _sessions(self):
        admin_token = await self.client.ensure_logged_in(
            settings.ADMIN_EMAIL, settings.ADMIN_PASSWORD, "Ikarin", "Admin"
        )
        user2_token = await self.client.ensure_logged_in(
            settings.SIM_USER2_EMAIL, settings.SIM_USER2_PASSWORD, "Ikarin", "Six"
        )
        admin_account_id = await self.client.get_main_account_id(admin_token)
        return admin_token, user2_token, admin_account_id

    async def tick(self) -> None:
        async with self._lock:
            await self._tick_unlocked()

    async def _tick_unlocked(self) -> None:
        self.last_tick_at = datetime.datetime.now(datetime.timezone.utc)
        try:
            admin_token, user2_token, admin_account_id = await self._sessions()
        except Exception:
            logger.exception("Failed to establish simulator sessions; skipping tick")
            return

        today = datetime.date.today()
        month_key = today.strftime("%Y-%m")

        if today.day in (1, 15):
            key = f"salary-{today.isoformat()}"
            if not self.state.is_done(key):
                await self._safe(self._fire_salary(admin_token, key))

        if today.day == 1:
            key = f"rent-{month_key}"
            if not self.state.is_done(key):
                await self._safe(self._fire_expense(
                    admin_token, admin_account_id, settings.RENT_AMOUNT_CENTS, "rent", RENT_MERCHANT, key
                ))

        if today.day == 5:
            key = f"car-insurance-{month_key}"
            if not self.state.is_done(key):
                await self._safe(self._fire_expense(
                    admin_token, admin_account_id, settings.CAR_INSURANCE_AMOUNT_CENTS,
                    "insurance", CAR_INSURANCE_MERCHANT, key
                ))

        if random.random() < settings.PURCHASE_CHANCE_PER_TICK:
            merchant = random_merchant()
            key = f"purchase-{uuid.uuid4()}"
            await self._safe(self._fire_expense(
                admin_token, admin_account_id, random_amount(merchant),
                merchant["category"], merchant["name"], key
            ))

        if random.random() < settings.P2P_CHANCE_PER_TICK:
            await self._safe(self._fire_p2p(admin_token, settings.SIM_USER2_EMAIL))
        if random.random() < settings.P2P_CHANCE_PER_TICK:
            await self._safe(self._fire_p2p(user2_token, settings.ADMIN_EMAIL))

    async def _fire_salary(self, admin_token: str, key: str) -> None:
        await self.client.admin_credit(
            admin_token, settings.ADMIN_EMAIL, settings.SALARY_AMOUNT_CENTS,
            "income", SALARY_SOURCE, "Biweekly salary deposit", key,
        )
        self.state.mark_done(key)
        logger.info("Fired salary deposit %s", key)

    async def _fire_expense(
        self, token: str, account_id: int, amount: int, category: str, merchant: str, key: str
    ) -> None:
        await self.client.expense(token, account_id, amount, category, merchant, idempotency_key=key)
        self.state.mark_done(key)
        logger.info("Fired expense %s: %s cents at %s (%s)", key, amount, merchant, category)

    async def _fire_p2p(self, token: str, recipient_email: str) -> None:
        amount = random.randint(1000, 15000)
        key = f"p2p-{uuid.uuid4()}"
        await self.client.p2p_transfer(token, recipient_email, amount, random.choice(P2P_MEMOS), key)
        logger.info("Fired P2P transfer %s to %s: %s cents", key, recipient_email, amount)

    @staticmethod
    async def _safe(coro) -> None:
        try:
            await coro
        except Exception:
            logger.exception("Simulated event failed")

    def status(self) -> dict:
        return {
            "last_tick_at": self.last_tick_at.isoformat() if self.last_tick_at else None,
            "tick_interval_seconds": settings.TICK_INTERVAL_SECONDS,
            "recent_events": self.state.recent(),
        }

    async def run_forever(self) -> None:
        while True:
            await self.tick()
            await asyncio.sleep(settings.TICK_INTERVAL_SECONDS)

    # --- Manual triggers for live demos: bypass date gating, use a unique key ---

    async def trigger_salary(self) -> dict:
        admin_token, _, _ = await self._sessions()
        key = f"salary-manual-{uuid.uuid4()}"
        await self._fire_salary(admin_token, key)
        return {"key": key}

    async def trigger_rent(self) -> dict:
        admin_token, _, admin_account_id = await self._sessions()
        key = f"rent-manual-{uuid.uuid4()}"
        await self._fire_expense(
            admin_token, admin_account_id, settings.RENT_AMOUNT_CENTS, "rent", RENT_MERCHANT, key
        )
        return {"key": key}

    async def trigger_insurance(self) -> dict:
        admin_token, _, admin_account_id = await self._sessions()
        key = f"car-insurance-manual-{uuid.uuid4()}"
        await self._fire_expense(
            admin_token, admin_account_id, settings.CAR_INSURANCE_AMOUNT_CENTS,
            "insurance", CAR_INSURANCE_MERCHANT, key
        )
        return {"key": key}

    async def trigger_purchase(self) -> dict:
        admin_token, _, admin_account_id = await self._sessions()
        merchant = random_merchant()
        key = f"purchase-manual-{uuid.uuid4()}"
        await self._fire_expense(
            admin_token, admin_account_id, random_amount(merchant),
            merchant["category"], merchant["name"], key
        )
        return {"key": key, "merchant": merchant["name"]}

    async def trigger_p2p(self) -> dict:
        admin_token, _, _ = await self._sessions()
        await self._fire_p2p(admin_token, settings.SIM_USER2_EMAIL)
        return {"status": "sent admin -> user2"}
