
import sys
import os
import unittest
from unittest.mock import MagicMock, patch, mock_open, AsyncMock
import json
import asyncio
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

modules_to_patch = {
    'confluent_kafka': MagicMock(),
    'clickhouse_connect': MagicMock()
}

with patch.dict(sys.modules, modules_to_patch):
    import consumer

class TestConsumer(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.mock_ch_client = MagicMock()
        # Patch BOTH get_clickhouse_client and the global ch_client
        self.patcher_ch = patch('consumer.get_clickhouse_client', return_value=self.mock_ch_client)
        self.patcher_ch.start()
        consumer.ch_client = self.mock_ch_client

    def tearDown(self):
        self.patcher_ch.stop()

    async def test_flush_to_clickhouse_async_success(self):
        """Test successful async flush to ClickHouse"""
        batch = [
            {
                "transaction_id": "tx1",
                "account_id": 1,
                "amount": 100.0,
                "category": "Test",
                "merchant": "Test Merchant",
                "timestamp": datetime.now().isoformat(),
                "transaction_type": "expense"
            }
        ]

        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(side_effect=lambda exec, f, *a: f(*a))
        
        with patch('asyncio.get_event_loop', return_value=mock_loop):
            result = await consumer.flush_to_clickhouse_async(batch)

        self.assertTrue(result)
        self.mock_ch_client.insert.assert_called_once()

        # Verify correct table and columns
        args, kwargs = self.mock_ch_client.insert.call_args
        self.assertEqual(args[0], "banking.transactions")
        self.assertIn("transaction_id", kwargs['column_names'])
        self.assertIn("parent_id", kwargs['column_names'])
    async def test_flush_to_clickhouse_async_failure_fallback(self):
        """Test fallback to sync flush if async fails"""
        batch = [{"transaction_id": "tx1", "account_id": 1, "amount": 100, "category": "cat", "merchant": "merch", "timestamp": "2023-01-01"}]

        # Make async call fail
        self.mock_ch_client.insert.side_effect = [Exception("Async fail"), None]
        
        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(side_effect=lambda exec, f, *a: f(*a))

        with patch('asyncio.get_event_loop', return_value=mock_loop):
            result = await consumer.flush_to_clickhouse_async(batch)

        self.assertTrue(result)
        self.assertEqual(self.mock_ch_client.insert.call_count, 2)

    def test_log_malformed_message_batch(self):
        """Test DLQ logging"""
        malformed = [
            {"partition": 0, "offset": 1, "error": "err", "raw_message": "bad_json"}
        ]

        with patch("builtins.open", mock_open()) as mock_file:
            consumer.log_malformed_message_batch(malformed)

            mock_file.assert_called_with("/tmp/kafka_dlq.jsonl", "a")
            handle = mock_file()
            handle.write.assert_called()

            # Check content
            args, _ = handle.write.call_args
            content = args[0]
            self.assertIn("bad_json", content)
            self.assertIn("err", content)

    async def test_consumer_loop_processing(self):
        """Test the main loop processing logic (mocked)"""
        # It's hard to test the infinite loop, but we can test components
        pass

if __name__ == '__main__':
    unittest.main()
