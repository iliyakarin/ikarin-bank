import asyncio
import logging
from v2.client_bank.mq_wrapper import ClientMQWrapper

logger = logging.getLogger(__name__)

class ClientBankService:
    """
    Simulates the business logic of a commercial bank interacting with the Fed Gateway.
    """
    def __init__(self, mq_wrapper: ClientMQWrapper):
        self.mq = mq_wrapper
        self._running = False

    async def start(self):
        """Starts the client bank service."""
        await self.mq.connect()
        self._running = True
        logger.info("Client Bank Service started.")

    async def stop(self):
        """Stops the client bank service."""
        self._running = False
        await self.mq.disconnect()
        logger.info("Client Bank Service stopped.")

    async def execute_payment(self, amount: float, currency: str, debtor: str, creditor: str, instr_id: str) -> str:
        """Executes a payment through the gateway."""
        logger.info(f"Executing payment {instr_id} for {amount} {currency}")
        corr_id = await self.mq.send_payment(amount, currency, debtor, creditor, instr_id)
        
        # Wait for the response (pacs.002)
        response = await self.mq.receive_response(timeout=5.0)
        if response and ("pacs.002" in response or "FtoFICsRppt" in response):
            logger.info(f"Payment {instr_id} processed successfully.")
            return response
        else:
            logger.error(f"Payment {instr_id} failed or timed out. Response: {response}")
            raise RuntimeError("Payment processing failed.")

    async def request_statement(self, account_id: str) -> str:
        """Requests a bank statement from the gateway."""
        logger.info(f"Requesting statement for {account_id}")
        await self.mq.request_statement(account_id)
        
        response = await self.mq.receive_response(timeout=5.0)
        if response and "camt.053" in response:
            logger.info(f"Statement for {account_id} received.")
            return response
        else:
            logger.error(f"Statement request for {account_id} failed.")
            raise RuntimeError("Statement request failed.")

    def log_info(self, msg: str):
        logger.info(msg)
