import asyncio
from typing import Optional
from v2.fed_gateway.transport.mq_client import MQClient


class ClientMQWrapper:
    """
    A simplified wrapper for the MQClient, specifically designed for the Client Bank.
    It abstracts the connection management and provides high-level methods for
    sending ISO 20022 messages.
    """
    def __init__(self):
        self.mq = MQClient()
        self._connected = False

    async def connect(self):
        """Establishes the connection to the Federal Gateway."""
        await self.mq.start()
        self._connected = True
        return True

    async def disconnect(self):
        """Closes the connection."""
        await self.mq.stop()
        self._connected = False
        return True

    async def send_payment(self, amount: float, currency: str, debtor: str, creditor: str, instr_id: str) -> str:
        """
        Sends a pacs.008 (Customer Credit Transfer) message.
        """
        if not self._connected:
            raise ConnectionError("Not connected to MQ network.")

        payload = self.mq.parser.create_pacs_008_payload(
            instruction_id=instr_id,
            amount=amount,
            currency=currency,
            debtor_account=debtor,
            creditor_account=creditor,
        )
        return await self.mq.send_message(payload)

    async def request_statement(self, account_id: str) -> str:
        """
        Sends a trigger for a camt.053 (Bank Statement) request.
        """
        if not self._connected:
            raise ConnectionError("Not connected to MQ network.")

        payload = f"<Request>Generate camt.053 for {account_id}</Request> (camt.053)"
        return await self.mq.send_message(payload)

    async def receive_response(self, timeout: float = 5.0) -> Optional[str]:
        """
        Waits for the next message on the queue and returns its payload.
        """
        if not self._connected:
            raise ConnectionError("Not connected to MQ network.")

        msg = await self.mq.get_next_outbound(timeout=timeout)
        return msg["payload"] if msg else None
