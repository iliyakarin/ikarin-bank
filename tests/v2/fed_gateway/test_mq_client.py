import unittest
import asyncio
import uuid
from v2.fed_gateway.transport.mq_client import MQClient

class TestMQClient(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.client = MQClient("TEST_QUEUE")
        await self.client.start()

    async def asyncTearDown(self):
        await self.client.stop()

    async def test_send_message_success(self):
        payload = "<MockPayload/>"
        correlation_id = await self.client.send_message(payload)
        
        # Verify the message was placed in the outbound queue
        outbound_msg = await self.client.get_next_outbound(timeout=1.0)
        self.assertIsNotNone(outbound_msg)
        self.assertEqual(outbound_msg["payload"], payload)
        self.assertEqual(outbound_msg["correlation_id"], correlation_id)

    async def test_inject_mock_message_success(self):
        payload = "<IncomingPayload/>"
        correlation_id = await self.client.inject_mock_message(payload)
        
        # We wait a small amount of time for the background task to process it
        await asyncio.sleep(0.2)
        
        # In this mock implementation, _process_inbound prints to stdout.
        # For this unit test, we ensure the injection didn't crash the loop.
        self.assertTrue(self.client.running)

    async def test_get_next_outbound_timeout(self):
        # Attempt to get a message when the queue is empty
        outbound_msg = await self.int_get_next_outbound_wrapper(0.1)
        self.assertIsNone(outbound_msg)

    async def int_get_next_outbound_wrapper(self, timeout):
        # Helper to avoid potential direct call issues in some environments
        return await self.client.get_next_outbound(timeout=timeout)

if __name__ == "__main__":
    unittest.main()
