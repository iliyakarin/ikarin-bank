import asyncio
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Union
from enum import Enum

class SettlementStatus(Enum):
    PENDING = "PENDING"
    SETTLED = "SETTLED"
    REJECTED = "REJECTED"
    TIMEOUT = "TIMEOUT"

class SettlementEngine:
    """
    Implements Fedwire (RTGS) and FedNow (Instant) settlement logic.
    Handles transaction finality, daylight overdraft checks, and status reporting.
    """

    def __init__(self, mq_client: any = None, max_overdraft_limit: Union[int, float, Decimal] = 1000000.0, initial_reserve_balance: Union[int, float, Decimal] = 5.0e6):
        self.mq_client = mq_client
        self.max_overdraft_limit = max_overdraft_limit
        self.active_reserves = initial_reserve_balance  # Simulated Fed Reserve Account balance
        self.transaction_ledger: Dict[str, Dict] = {}

    async def process_fednow_payment(
        self, 
        transaction_id: str, 
        amount: Union[int, float, Decimal], 
        parser: any = None,
        currency: str = "USD"
    ) -> Dict:
        """
        Simulates FedNow Instant Settlement.
        Provides sub-second finality and immediate status return via async loop.
        """
        if amount <= 0:
            result = self._finalize_transaction(transaction_id, SettlementStatus.REJECTED, "Amount must be positive")
        elif amount > self.active_reserves:
            result = self._finalize_transaction(transaction_id, SettlementStatus.REJECTED, "Insufficient liquidity in Fed account")
        else:
            self.active_reserves -= amount
            result = self._finalize_transaction(transaction_id, SettlementStatus.SETTLED)

        # Generate and send the pacs.002 response via the MQ Client
        if self.mq_client and parser:
            pacs_002_payload = parser.create_pacs_002_payload(
                transaction_id,
                result["status"],
                transaction_id,
                result.get("reason", "")
            )
            await self.mq_client.send_message(pacs_002_payload, correlation_id=transaction_id)

        return result

    async def process_fedwire_payment(
        self, 
        transaction_id: str, 
        amount: Union[int, float, Decimal], 
        parser: any = None,
        currency: str = "USD"
    ) -> Dict:
        """
        Simulates Fedwire Funds Service (RTGS).
        Handles high-value gross settlements with potential for daylight overdrafts.
        """
        if amount <= 0:
            result = self._finalize_transaction(transaction_id, SettlementStatus.REJECTED, "Amount must be positive")
        elif amount > (self.active_reserves + self.max_overdraft_limit):
            result = self._finalize_transaction(transaction_id, SettlementStatus.REJECTED, "Exceeds daylight overdraft limit")
        else:
            self.active_reserves -= amount
            result = self._finalize_transaction(transaction_id, SettlementStatus.SETTLED)

        # Generate and send the pacs.002 response via the MQ Client
        if self.mq_client and parser:
            pacs_002_payload = parser.create_pacs_002_payload(
                transaction_id,
                result["status"],
                transaction_id,
                result.get("for_reason", result.get("reason", ""))
            )
            await self.mq_client.send_message(pacs_002_payload, correlation_id=transaction_id)

        return result

    def _finalize_transaction(self, transaction_id: str, status: SettlementStatus, reason: str = "") -> Dict:
        """Internal helper to record and finalize transaction state."""
        record = {
            "transaction_id": transaction_id,
            "status": status.value,
            "timestamp": datetime.utcnow().isoformat(),
            "reason": reason
        }
        self.transaction_ledger[transaction_id] = record
        return record

    def get_account_balance(self) -> float:
        """Returns the current virtual Fed reserve balance."""
        return self.active_reserves

    def get_transaction_status(self, transaction_id: str) -> Optional[Dict]:
        """Retrieves the status of a particular transaction."""
        return self.transaction_ledger.get(transaction_id)

    async def generate_camt_053_statement(self, account_id: str) -> str:
        """Generates a camt.053 XML payload."""
        timestamp = datetime.utcnow().isoformat()
        balance = self.get_account_balance()
        return f'<camt.053><Id>{account_id}</Id><Bal>{balance}</Bal><Dt>{timestamp}</Dt></camt.053>'
