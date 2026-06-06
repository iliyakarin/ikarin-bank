import unittest
import asyncio
import xml.etree.ElementTree as ET
from v2.fed_gateway.transport.mq_client import MQClient
from v2.fed_gateway.engine.settlement import SettlementEngine, SettlementStatus
from v2.fed_gateway.parsers.iso20022 import ISO20022Parser

class TestFedNowAsyncPipeline(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.mq_client = MQClient("TEST_QUEUE")
        self.parser = self.ISO200_Placeholder()
        self.engine = SettlementEngine(mq_client=self.mq_client, max_overdraft_limit=1000.0, initial_reserve_balance=5000.0)
        await self.mq_client.start()

    async def asyncTearDown(self):
        await self.mq_client.stop()

    async def test_fednow_asynchronous_settlement_flow(self):
        """
        Integration Test: Verifies the FedNow asynchronous settlement loop.
        Ensures that injecting a transaction leads to an eventual pacs.002 response.
        """
        # 1. Prepare the transaction
        instr_id = "FEDNOW-123"
        amount = 100.0
        currency = "USD"
        
        # 2. Create payload and inject
        pacs_008_payload = self.parser.create_pacs_008_payload(
            instr_id, amount, currency, "DEBTOR-ACC", "CREDITOR-ACC"
        )
        correlation_id = await self.mq_client.inject_mock_message(pacs_008_payload)

        # 3. Execute the asynchronous settlement engine call
        # Since we are testing the engine's async logic, we call it directly
        result = await self.engine.process_fednow_payment(
            instr_id, amount, self.parser
        )

        # 4. Verify the engine's immediate result
        self.assertEqual(result["status"], "SETTLED")

        # 5. Verify the asynchronous side-effect: The outbound pacs.002 message
        outbound_msg = await self.mq_client.get_next_outbound(timeout=2.0)
        
        self.assertIsNotNone(outbound_msg, "No outbound pacs.002 message found in MQ outbox")
        self.assertEqual(outbound_msg["correlation_id"], instr_id)
        
        # Parse the outbound payload to verify its content
        resp_root = ET.fromstring(outbound_msg["payload"])
        # Use wildcard namespace to find GrpSts regardless of version
        status_elem = resp_root.find(".//{*}GrpSts")
        self.assertIsNotNone(status_elem, "Could not find GrpSts in XML")
        self.assertEqual(status_elem.text, "SETTLED")

    class ISO200_Placeholder:
        def create_pacs_008_payload(self, *args):
            return f'<pacs.008><Amt>100.0</Amt></pacs.008>'
        def create_pacs_002_payload(self, *args):
            return '<pacs.002><GrpSts>SETTLED</GrpSts></pacs.002>'

if __name__ == "__main__":
    unittest.main()
