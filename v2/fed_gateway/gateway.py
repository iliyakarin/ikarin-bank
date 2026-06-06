import asyncio
import logging
from v2.fed_gateway.transport.mq_client import MQClient
from v2.fed_gateway.parsers.iso20022 import ISO20022Parser
from v2.fed_gateway.engine.settlement import SettlementEngine

logger = logging.getLogger(__name__)

class FedGatewayHost:
    """
    The main orchestrator for the FedLine Direct v2 Gateway.
    Listens to MQ, parses ISO 20022, and executes settlement.
    """

    def __init__(self, mq_client: MQClient, settlement_engine: SettlementEngine):
        self.mq = mq_client
        self.engine = settlement_engine
        self.parser = ISO20022Parser()
        self.running = False

    async def start(self):
        """Starts the gateway processing loop."""
        self.running = True
        print("[*] FedGatewayHost v2 started.")
        asyncio.create_task(self._run_loop())

    async def stop(self):
        """Stops the gateway."""

        self.running = False
        print("[*] FedGatewayHost v2 stopped.")

    async def _run_loop(self):
        """The main processing loop: Inbound MQ -> Parse -> Settle -> Outbound MQ."""
        while self.running:
            # 1. Wait for an outbound message (simulating an inbound request from the network)
            # In a real system, we would listen to the 'inbox' via the MQ client.
            # For this simulation, we poll the 'outbox' to see what the 'network' sent us.
            msg = await self.mq.get_next_outbound(timeout=1.0)
            
            if msg:
                print(f"[Gateway] Received message: {msg['correlation_id']}")
                await self._handle_message(msg)
            
            await asyncio.sleep(0.1)

    async def _handle_message(self, msg: dict):
        """Dispatches the message to the correct handler based on payload type."""
        payload = msg["payload"]
        correlation_id = msg["correlation_id"]
        
        try:
            # 2. Identify message type (Simplified: check for pacs.008 in XML)
            if "pacs.008" in payload:
                print(f"[Gateway] Processing Fedwire (pacs.008) for {correlation_id}")
                # In a real app, we'd parse the XML to extract details.
                # For simulation, we assume the payload contains the amount/details.
                # We'll use a dummy parsing step here.
                await self._handle_fedwire(payload, correlation_id)
            
            elif "pacs_002" in payload: # Simulation of status report
                 print(f"[Gateway] Processing Status Report (pacs.002) for {correlation_id}")
                 pass
            else:
                print(f"[Gateway] Unknown message type in {correlation_id}")

        except Exception as e:
            print(f"[Gateway] Error processing {correlation_id}: {e}")
            # In a real system, we would send a pacs.002 REJECT message back via MQ.

    async def _handle_fedwire(self, payload: str, correlation_t_id: str):
        """Processes a Fedwire (RTGS) payment."""
        # 3. Perform Settlement
        # We extract a dummy amount for the simulation.
        # Real implementation would use the ISO20022Parser to extract this from the XML.
        amount = 5000.0 # Dummy amount for simulation
        
        result = self.engine.process_fedwire_payment(
            transaction_id=correlation_t_id, 
            amount=amount
        )
        
        # 4. Generate and Send Status Report (pacs.002)
        status_payload = f"<pacs.002><Status>{result['status']}</Status><Reason>{result['reason']}</Reason></pacs.00ss>"
        await self.mq.send_message(status_payload, correlation_id=correlation_t_id)
        print(f"[Gateway] Sent status {result['status']} back to MQ.")

    async def _handle_fednow(self, payload: str, correlation_id: str):
        """Processes a FedNow (Instant) payment."""
        amount = 100.0 # Dummy amount
        result = self.engine.process_fednow_payment(
            transaction_id=correlation_id, 
            amount=amount
        )
        
        status_payload = f"<pacs.002><Status>{result['status']}</Status></pacs.002>"
        await self.mq.send_message(status_payload, correlation_id=correlation_id)
        print(f"[Gateway] Sent status {result['status']} back to MQ.")

if __name__ == "__main__":
    # For standalone testing
    async def main():
        mq = MQClient()
        engine = SettlementEngine()
        gateway = FedGatewayHost(mq, engine)
        await mq.start()
        await gateway.start()
        
        # Inject a test message
        await mq.inject_mock_message("<pacs.008>...</pacs.008>")
        
        await asyncio.sleep(2)
        await gateway.stop()
        await mq.stop()

    asyncio.run(main())
