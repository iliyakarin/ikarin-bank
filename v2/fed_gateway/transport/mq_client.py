import asyncio
import random
import uuid
from datetime import datetime
from v2.fed_gateway.parsers.iso20022 import ISO20022Parser

class MQClient:
    """
    Simulates an IBM MQ client for FedLine Direct.
    Handles message ingestion, correlation IDs, and asynchronous transport.
    """

    def __init__(self, queue_name: str = "FEDLINE_DIRECT_QUEUE"):
        self.queue_name = queue_name
        self.parser = ISO20022Parser()
        self.inbox = asyncio.Queue()
        self.outbox = asyncio.Queue()
        self.running = False

    async def start(self):
        """Starts the MQ consumer/producer loop."""
        self.running = True
        print(f"[*] MQ Client connected to {self.queue_name}")
        asyncio.create_task(self._process_inbound())

    async def stop(self):
        """Gracefully shuts down the MQ connection."""
        self.running = False
        print("[*] MQ Client disconnected.")

    async def send_message(self, payload: str, correlation_id: str = None):
        """Sends an XML message to the outbound queue."""
        msg = {
            "payload": payload,
            "correlation_id": correlation_id or str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.outbox.put(msg)
        return msg["correlation_id"]

    async def _process_inbound(self):
        """Simulates the background ingestion of messages from the network."""
        while self.running:
            if not self.inbox.empty():
                msg = await self.inbox.get()
                print(f"[MQ] Inbound: {msg['correlation_id']} processed.")
                self.inbox.task_done()
            await asyncio.sleep(0.1)

    async def inject_mock_message(self, payload: str):
        """Helper for testing: injects a message into the simulated inbound queue."""
        correlation_id = str(uuid.uuid4())
        await self.inbox.put({
            "payload": payload,
            "correlation_id": correlation_id,
            "timestamp": datetime.utcnow().isoformat()
        })
        return correlation_id

    async def get_next_outbound(self, timeout: float = 1.0):
        """Retrieves the next message from the outbound queue (for verification)."""
        try:
            return await asyncio.wait_for(self.outbox.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None
