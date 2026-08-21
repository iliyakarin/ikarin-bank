"""Core simulation loop: decides what financial events to fire on each tick.

Simulates a full realistic financial life across checking & savings accounts,
utility bills, card top-ups, P2P transfers, payment requests, and auto-savings.
"""
import asyncio
import datetime
import logging
import random
import uuid
from typing import Optional, Tuple, Dict, Any

from client import ApiClient
from config import settings
from state import EventState
from scenarios import (
    random_merchant, random_amount, RENT_MERCHANT, CAR_INSURANCE_MERCHANT,
    SALARY_SOURCE, UTILITY_BILLS, CARD_DEPOSIT_SCENARIOS, P2P_MEMOS,
    PAYMENT_REQUEST_SCENARIOS, FEDWIRE_SCENARIOS, FEDNOW_SCENARIOS, FEDACH_SCENARIOS,
)

logger = logging.getLogger(__name__)


class FinancialLifeSimulator:
    def __init__(self):
        self.client = ApiClient(settings.API_BASE_URL)
        self.state = EventState(settings.STATE_DB_PATH)
        self.last_tick_at: Optional[datetime.datetime] = None
        self._lock = asyncio.Lock()

    async def _sessions(self) -> Tuple[str, str, Dict[str, Any], Dict[str, Any]]:
        """Logs in both demo personas, ensures contacts and savings accounts exist."""
        admin_token = await self.client.ensure_logged_in(
            settings.ADMIN_EMAIL, settings.ADMIN_PASSWORD, "Ikarin", "Admin"
        )
        user2_token = await self.client.ensure_logged_in(
            settings.SIM_USER2_EMAIL, settings.SIM_USER2_PASSWORD, "Ikarin", "Six"
        )

        # Ensure reciprocal contacts in address books
        await self._safe(self.client.ensure_contact(admin_token, "Ikarin Six", settings.SIM_USER2_EMAIL, "Friend"))
        await self._safe(self.client.ensure_contact(user2_token, "Ikarin Admin", settings.ADMIN_EMAIL, "Family"))

        # Main Checking Account & Sub-Savings Account
        admin_main = await self.client.get_main_account_info(admin_token)
        admin_savings = await self.client.ensure_savings_account(admin_token, "High Yield Savings")

        return admin_token, user2_token, admin_main, admin_savings

    async def tick(self) -> None:
        async with self._lock:
            await self._tick_unlocked()

    async def _tick_unlocked(self) -> None:
        self.last_tick_at = datetime.datetime.now(datetime.timezone.utc)
        try:
            admin_token, user2_token, admin_main, admin_savings = await self._sessions()
            checking_id = admin_main["id"]
            savings_id = admin_savings["id"]
            current_balance = admin_main["balance"]
        except Exception:
            logger.exception("Failed to establish simulator sessions; skipping tick")
            return

        utc_now = datetime.datetime.now(datetime.timezone.utc)
        today = utc_now.date()
        month_key = today.strftime("%Y-%m")
        is_weekend = today.weekday() >= 5
        est_hour = (utc_now.hour - 5) % 24
        is_daytime = 8 <= est_hour <= 22

        time_slot = "any"
        if 7 <= est_hour < 11:
            time_slot = "morning"
        elif 11 <= est_hour < 16:
            time_slot = "day"
        elif 16 <= est_hour < 23:
            time_slot = "evening"

        # 1. Salary & Automatic Savings (1st and 15th of the month)
        if today.day in (1, 15):
            salary_key = f"salary-{today.isoformat()}"
            if not self.state.is_done(salary_key):
                await self._safe(self._fire_salary(admin_token, salary_key))
                current_balance += settings.SALARY_AMOUNT_CENTS

                # Auto-transfer 15% to Savings Account
                savings_amount = int(settings.SALARY_AMOUNT_CENTS * 0.15)
                savings_key = f"auto-savings-{today.isoformat()}"
                if not self.state.is_done(savings_key) and checking_id != savings_id:
                    await self._safe(self._fire_savings_transfer(
                        admin_token, checking_id, savings_id, savings_amount,
                        "Auto-save 15% from biweekly paycheck", savings_key
                    ))
                    current_balance -= savings_amount

        # 2. Monthly Rent (1st of the month)
        if today.day == 1:
            rent_key = f"rent-{month_key}"
            if not self.state.is_done(rent_key):
                current_balance = await self._ensure_funds(
                    admin_token, checking_id, savings_id, current_balance, settings.RENT_AMOUNT_CENTS
                )
                await self._safe(self._fire_expense(
                    admin_token, checking_id, settings.RENT_AMOUNT_CENTS, "rent", RENT_MERCHANT, rent_key
                ))
                current_balance -= settings.RENT_AMOUNT_CENTS

        # 3. Monthly Car Insurance (5th of the month)
        if today.day == 5:
            ins_key = f"car-insurance-{month_key}"
            if not self.state.is_done(ins_key):
                await self._safe(self._fire_expense(
                    admin_token, checking_id, settings.CAR_INSURANCE_AMOUNT_CENTS,
                    "insurance", CAR_INSURANCE_MERCHANT, ins_key
                ))
                current_balance -= settings.CAR_INSURANCE_AMOUNT_CENTS

        # 4. Monthly Utilities & Telecom Bills
        for bill in UTILITY_BILLS:
            if today.day == bill["day"]:
                bill_key = f"utility-{bill['name'].lower().replace(' ', '-')}-{month_key}"
                if not self.state.is_done(bill_key):
                    amount = random.randint(bill["min_cents"], bill["max_cents"])
                    current_balance = await self._ensure_funds(
                        admin_token, checking_id, savings_id, current_balance, amount
                    )
                    await self._safe(self._fire_vendor_bill(
                        admin_token, bill["email"], amount, bill["subscriber_id"],
                        f"Monthly bill for {bill['name']}", bill_key
                    ))
                    current_balance -= amount

        # 5. Stochastic Activities during daytime ticks
        activity_multiplier = 1.5 if is_daytime else 0.1
        purchase_chance = settings.PURCHASE_CHANCE_PER_TICK * activity_multiplier
        p2p_chance = settings.P2P_CHANCE_PER_TICK * activity_multiplier
        deposit_chance = 0.04 * activity_multiplier
        request_chance = 0.05 * activity_multiplier

        # A. Retail / Merchant Purchase
        if random.random() < purchase_chance:
            merchant = random_merchant(time_slot=time_slot, is_weekend=is_weekend)
            spend_multiplier = 1.25 if is_weekend else 1.0
            amount = random_amount(merchant, multiplier=spend_multiplier)
            if current_balance >= amount:
                key = f"purchase-{uuid.uuid4()}"
                await self._safe(self._fire_expense(
                    admin_token, checking_id, amount,
                    merchant["category"], merchant["name"], key
                ))
                current_balance -= amount

        # B. External Card Deposit (e.g. Freelance payout, gift, reimbursement)
        if random.random() < deposit_chance:
            scenario = random.choice(CARD_DEPOSIT_SCENARIOS)
            amount = random.randint(scenario["min_cents"], scenario["max_cents"])
            key = f"card-deposit-{uuid.uuid4()}"
            await self._safe(self._fire_card_deposit(admin_token, amount, key))
            current_balance += amount

        # C. Payment Request & Fulfillment
        if random.random() < request_chance:
            req_scenario = random.choice(PAYMENT_REQUEST_SCENARIOS)
            req_amount = random.randint(req_scenario["min_cents"], req_scenario["max_cents"])
            await self._safe(self._fire_social_split(
                user2_token, admin_token, settings.ADMIN_EMAIL, settings.SIM_USER2_EMAIL,
                req_amount, req_scenario["purpose"]
            ))

        # D. P2P Direct Transfers
        if random.random() < p2p_chance:
            amount = random.randint(1200, 15000)
            if current_balance >= amount:
                key = f"p2p-{uuid.uuid4()}"
                await self._safe(self._fire_p2p(admin_token, settings.SIM_USER2_EMAIL, amount, key))
                current_balance -= amount

        if random.random() < p2p_chance:
            amount = random.randint(1200, 15000)
            key = f"p2p-{uuid.uuid4()}"
            await self._safe(self._fire_p2p(user2_token, settings.ADMIN_EMAIL, amount, key))

    async def _ensure_funds(
        self, token: str, checking_id: int, savings_id: int, current_balance: int, required_amount: int
    ) -> int:
        """If checking balance is low, transfers emergency funds from savings."""
        if current_balance < required_amount and checking_id != savings_id:
            deficit = required_amount - current_balance + 20000  # replenish deficit + $200 buffer
            key = f"savings-withdraw-{uuid.uuid4()}"
            logger.info("Checking balance low (%s cents); transferring %s from savings", current_balance, deficit)
            try:
                await self.client.internal_transfer(
                    token, savings_id, checking_id, deficit,
                    "Emergency transfer from High-Yield Savings", key
                )
                self.state.mark_done(key)
                return current_balance + deficit
            except Exception:
                logger.warning("Could not auto-transfer from savings; proceeding with current balance")
        return current_balance

    # --- Core Event Execution Methods ---

    async def _fire_salary(self, admin_token: str, key: str) -> None:
        await self.client.admin_credit(
            admin_token, settings.ADMIN_EMAIL, settings.SALARY_AMOUNT_CENTS,
            "income", SALARY_SOURCE, "Biweekly salary deposit", key,
        )
        self.state.mark_done(key)
        logger.info("Fired salary deposit %s: %s cents", key, settings.SALARY_AMOUNT_CENTS)

    async def _fire_savings_transfer(
        self, token: str, from_id: int, to_id: int, amount: int, commentary: str, key: str
    ) -> None:
        await self.client.internal_transfer(token, from_id, to_id, amount, commentary, key)
        self.state.mark_done(key)
        logger.info("Fired auto-savings transfer %s: %s cents from #%s to #%s", key, amount, from_id, to_id)

    async def _fire_expense(
        self, token: str, account_id: int, amount: int, category: str, merchant: str, key: str
    ) -> None:
        await self.client.expense(token, account_id, amount, category, merchant, idempotency_key=key)
        self.state.mark_done(key)
        logger.info("Fired expense %s: %s cents at %s (%s)", key, amount, merchant, category)

    async def _fire_vendor_bill(
        self, token: str, vendor_email: str, amount: int, subscriber_id: str, commentary: str, key: str
    ) -> None:
        await self.client.p2p_transfer(
            token, vendor_email, amount, commentary, idempotency_key=key, subscriber_id=subscriber_id
        )
        self.state.mark_done(key)
        logger.info("Fired vendor bill %s: %s cents to %s (Sub: %s)", key, amount, vendor_email, subscriber_id)

    async def _fire_card_deposit(self, token: str, amount: int, key: str) -> None:
        await self.client.create_card_deposit(token, amount, key)
        self.state.mark_done(key)
        logger.info("Fired card deposit %s: %s cents", key, amount)

    async def _fire_p2p(self, token: str, recipient_email: str, amount: int = None, key: str = None) -> None:
        amount = amount or random.randint(1200, 15000)
        key = key or f"p2p-{uuid.uuid4()}"
        memo = random.choice(P2P_MEMOS)
        await self.client.p2p_transfer(token, recipient_email, amount, memo, key)
        self.state.mark_done(key)
        logger.info("Fired P2P transfer %s to %s: %s cents ('%s')", key, recipient_email, amount, memo)

    async def _fire_social_split(
        self, requester_token: str, payer_token: str, payer_email: str, requester_email: str,
        amount: int, purpose: str
    ) -> None:
        """User2 creates a payment request to Admin, who fulfills it."""
        req_res = await self.client.create_payment_request(requester_token, payer_email, amount, purpose)
        req_id = req_res.get("request_id")
        if req_id:
            key = f"pay-request-{req_id}-{uuid.uuid4()}"
            await self.client.p2p_transfer(
                payer_token, requester_email, amount, f"Settled: {purpose}",
                idempotency_key=key, payment_request_id=req_id
            )
            self.state.mark_done(key)
            logger.info("Fired social split payment for request #%s: %s cents ('%s')", req_id, amount, purpose)

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

    # --- Manual Trigger Handlers for Inspection & Demonstrations ---

    async def trigger_salary(self) -> dict:
        """Fires salary deposit and auto-allocates 15% to savings."""
        admin_token, _, admin_main, admin_savings = await self._sessions()
        key = f"salary-manual-{uuid.uuid4()}"
        await self._fire_salary(admin_token, key)

        savings_key = f"auto-savings-manual-{uuid.uuid4()}"
        savings_amount = int(settings.SALARY_AMOUNT_CENTS * 0.15)
        if admin_main["id"] != admin_savings["id"]:
            await self._fire_savings_transfer(
                admin_token, admin_main["id"], admin_savings["id"], savings_amount,
                "Manual auto-savings from salary", savings_key
            )
        return {
            "salary_key": key,
            "amount_credited_cents": settings.SALARY_AMOUNT_CENTS,
            "savings_key": savings_key,
            "savings_transferred_cents": savings_amount,
        }

    async def trigger_savings(self) -> dict:
        """Manually transfers money from Checking to Savings."""
        admin_token, _, admin_main, admin_savings = await self._sessions()
        if admin_main["id"] == admin_savings["id"]:
            return {"error": "Savings account identical to checking account"}
        amount = 25000  # $250.00
        key = f"savings-deposit-manual-{uuid.uuid4()}"
        await self._fire_savings_transfer(
            admin_token, admin_main["id"], admin_savings["id"], amount,
            "Manual contribution to High-Yield Savings", key
        )
        return {"key": key, "amount_cents": amount, "to_account": admin_savings["name"]}

    async def trigger_deposit_card(self) -> dict:
        """Fires an external debit/credit card deposit via mock payment gateway."""
        admin_token, _, _, _ = await self._sessions()
        amount = random.randint(15000, 50000)
        key = f"card-deposit-manual-{uuid.uuid4()}"
        result = await self.client.create_card_deposit(admin_token, amount, key)
        self.state.mark_done(key)
        return {"key": key, "amount_cents": amount, "result": result}

    async def trigger_utility_bills(self) -> dict:
        """Fires payments for Austin Energy and T-Mobile."""
        admin_token, _, _, _ = await self._sessions()
        results = []
        for bill in UTILITY_BILLS:
            amount = random.randint(bill["min_cents"], bill["max_cents"])
            key = f"utility-manual-{bill['name'].lower().replace(' ', '-')}-{uuid.uuid4()}"
            await self._fire_vendor_bill(
                admin_token, bill["email"], amount, bill["subscriber_id"],
                f"Manual utility payment for {bill['name']}", key
            )
            results.append({"vendor": bill["name"], "amount_cents": amount, "key": key})
        return {"bills_paid": results}

    async def trigger_payment_request(self) -> dict:
        """Simulates User2 requesting money from Admin and Admin paying it."""
        admin_token, user2_token, _, _ = await self._sessions()
        scenario = random.choice(PAYMENT_REQUEST_SCENARIOS)
        amount = random.randint(scenario["min_cents"], scenario["max_cents"])
        await self._fire_social_split(
            user2_token, admin_token, settings.ADMIN_EMAIL, settings.SIM_USER2_EMAIL,
            amount, scenario["purpose"]
        )
        return {"requester": settings.SIM_USER2_EMAIL, "payer": settings.ADMIN_EMAIL, "purpose": scenario["purpose"], "amount_cents": amount}

    async def trigger_rent(self) -> dict:
        admin_token, _, admin_main, _ = await self._sessions()
        key = f"rent-manual-{uuid.uuid4()}"
        await self._fire_expense(
            admin_token, admin_main["id"], settings.RENT_AMOUNT_CENTS, "rent", RENT_MERCHANT, key
        )
        return {"key": key, "amount_cents": settings.RENT_AMOUNT_CENTS}

    async def trigger_insurance(self) -> dict:
        admin_token, _, admin_main, _ = await self._sessions()
        key = f"car-insurance-manual-{uuid.uuid4()}"
        await self._fire_expense(
            admin_token, admin_main["id"], settings.CAR_INSURANCE_AMOUNT_CENTS,
            "insurance", CAR_INSURANCE_MERCHANT, key
        )
        return {"key": key, "amount_cents": settings.CAR_INSURANCE_AMOUNT_CENTS}

    async def trigger_purchase(self) -> dict:
        admin_token, _, admin_main, _ = await self._sessions()
        merchant = random_merchant()
        amount = random_amount(merchant)
        key = f"purchase-manual-{uuid.uuid4()}"
        await self._fire_expense(
            admin_token, admin_main["id"], amount,
            merchant["category"], merchant["name"], key
        )
        return {"key": key, "merchant": merchant["name"], "amount_cents": amount}

    async def trigger_p2p(self) -> dict:
        admin_token, _, _, _ = await self._sessions()
        amount = random.randint(1500, 10000)
        key = f"p2p-manual-{uuid.uuid4()}"
        await self._fire_p2p(admin_token, settings.SIM_USER2_EMAIL, amount, key)
        return {"key": key, "amount_cents": amount, "recipient": settings.SIM_USER2_EMAIL}

    async def trigger_wire(self) -> dict:
        admin_token, _, admin_main, _ = await self._sessions()
        scen = random.choice(FEDWIRE_SCENARIOS)
        amount = random.randint(scen["min_cents"], scen["max_cents"])
        key = f"fedwire-manual-{uuid.uuid4()}"
        res = await self.client.wire_transfer(
            token=admin_token,
            account_id=admin_main["id"],
            amount=amount,
            receiver_routing=scen["receiver_routing"],
            receiver_name=scen["receiver_name"],
            receiver_account=scen["receiver_account"],
            payment_reference=scen["payment_reference"],
            idempotency_key=key,
        )
        return {"key": key, "imad": res.get("imad"), "amount_cents": amount, "receiver": scen["receiver_name"]}

    async def trigger_fednow(self) -> dict:
        admin_token, _, admin_main, _ = await self._sessions()
        scen = random.choice(FEDNOW_SCENARIOS)
        amount = random.randint(scen["min_cents"], scen["max_cents"])
        key = f"fednow-manual-{uuid.uuid4()}"
        res = await self.client.fednow_transfer(
            token=admin_token,
            account_id=admin_main["id"],
            amount=amount,
            creditor_routing=scen["creditor_routing"],
            creditor_name=scen["creditor_name"],
            creditor_account=scen["creditor_account"],
            remittance_info=scen["remittance_info"],
            idempotency_key=key,
        )
        return {"key": key, "end_to_end_id": res.get("end_to_end_id"), "amount_cents": amount, "creditor": scen["creditor_name"]}

    async def trigger_ach(self) -> dict:
        admin_token, _, admin_main, _ = await self._sessions()
        scen = random.choice(FEDACH_SCENARIOS)
        amount = random.randint(scen["min_cents"], scen["max_cents"])
        key = f"ach-manual-{uuid.uuid4()}"
        res = await self.client.ach_transfer(
            token=admin_token,
            account_id=admin_main["id"],
            amount=amount,
            receiver_routing=scen["receiver_routing"],
            receiver_name=scen["receiver_name"],
            receiver_account=scen["receiver_account"],
            payment_description=scen["payment_description"],
            idempotency_key=key,
        )
        return {"key": key, "trace_number": res.get("trace_number"), "amount_cents": amount, "receiver": scen["receiver_name"]}

    async def trigger_full_cycle(self) -> dict:
        """Simulates an entire month's comprehensive financial journey in sequence."""
        salary_res = await self.trigger_salary()
        rent_res = await self.trigger_rent()
        ins_res = await self.trigger_insurance()
        util_res = await self.trigger_utility_bills()
        card_res = await self.trigger_deposit_card()
        purch_res = await self.trigger_purchase()
        req_res = await self.trigger_payment_request()
        p2p_res = await self.trigger_p2p()
        wire_res = await self.trigger_wire()
        now_res = await self.trigger_fednow()
        ach_res = await self.trigger_ach()

        return {
            "cycle_status": "completed",
            "events": {
                "salary_and_savings": salary_res,
                "rent": rent_res,
                "insurance": ins_res,
                "utilities": util_res,
                "external_card_deposit": card_res,
                "retail_purchase": purch_res,
                "social_payment_request": req_res,
                "p2p_transfer": p2p_res,
                "fedwire_rtgs": wire_res,
                "fednow_instant": now_res,
                "fedach_transfer": ach_res,
            }
        }
