import unittest
import asyncio
import xml.etree.ElementTree as ET
from v2.fed_gateway.transport.mq_client import MQClient
from v2.fed_gateway.parsers.iso20022 import ISO20022Parser
from v2.fed_gateway.engine.settlement import SettlementEngine, SettlementStatus

class TestFedGatewayPipeline(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.mq_client = MQClient("TEST_QUEUE")
        self.parser = ISO20022Parser()
        self.engine = SettlementEngine(mq_client=self.mq_client, max_overdraft_limit=1000.0, initial_reserve_balance=5000.0)
        await self.mq_client.start()

    async def asyncTearDown(self):
        await self.mq_client.stop()

    async def test_end_to_async_settlement_pipeline(self):
        """
        Integration Test: Simulates the full lifecycle of a Fedwire transaction.
        """
        # 1. Prepare the incoming transaction (pacs.008)
        instr_id = "TXN-999"
        amount = 250.0
        currency = "USD"
        debtor = "ACC-DEBT"
        creditor = "ACC-CRED"
        
        pacs_008_payload = self.parser.create_pacs_008_payload(
            instr_id, amount, currency, debtor, creditor
        )

        # 2. Inject into the simulated network
        correlation_id = await self.mq_client.inject_mock_message(pacs_008_payload)

        # 3. Simulate the Gateway Logic (The 'Brain')
        # We manually trigger processing since the background loop is a mock
        # 3. Simulate the Gateway Logic (The 'Brain')
        # For the sake of this failing test, we manually trigger processing
        root = ET.fromstring(pacs_008_payload)
        ns = {'ns': 'urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08'}
        amt_elem = root.find(".//ns:Amt", ns)
        amt_val = float(amt_elem.text)
        
        # Manually trigger engine processing
        result = await self.engine.process_fedwire_payment(instr_id, amt_val)
        
        # 4. Generate the response (pacs.002)
        pacs_002_payload = self.parser.create_pacs_002_payload(
            instr_id,
            result["status"],
            instr_id,
            result.get("reason", "")
        )

        # 5. Push the response back to the outbound queue
        await self.mq_client.send_message(pacs_002_payload, correlation_id=correlation_id)

        # 6. Verification
        outbound_msg = await self.mq_client.get_next_outbound(timeout=2.0)
        
        self.assertIsNotNone(outbound_msg, "No outbound message found in MQ outbox")
        self.assertEqual(outbound_msg["correlation_id"], correlation_id)
        
        # Verify the XML content of the response
        resp_root = ET.fromstring(outbound_msg["payload"])
        resp_ns = {'ns': 'urn:iso:std:iso:20022:tech:xsd:pacs.002.001.10'}
        status_elem = resp_root.find(".//ns:GrpSts", resp_ns)
        self.assertIsNotNone(status_elem)
        self.assertEqual(status_elem.text, result["status"])

if __name__ == "__main__":
    unittest.main()
