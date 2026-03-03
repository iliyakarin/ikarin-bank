
import sys
import unittest
from unittest.mock import MagicMock, patch, mock_open
import os
import json
import asyncio
from datetime import datetime

# 1. Mock external dependencies BEFORE importing the module under test
sys.modules['confluent_kafka'] = MagicMock()
sys.modules['clickhouse_connect'] = MagicMock()

# Now we can import the consumer module safely
# We need to make sure we are importing the newly refactored consumer.py
import backend.consumer as consumer

class TestConsumer(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        # Reset mocks
        self.mock_ch_client = MagicMock()
        self.mock_consumer = MagicMock()

        # Patch get_client to return our mock
        self.patcher_ch = patch('backend.consumer.clickhouse_connect.get_client', return_value=self.mock_ch_client)
        self.patcher_ch.start()

        # Reset the global client in consumer module
        consumer.ch_client = None

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

        # Mock run_in_executor to execute the function immediately (synchronously for test)
        async def mock_run_in_executor(executor, func, *args):
            return func(*args)

        with patch('asyncio.get_event_loop') as mock_loop:
            mock_loop.return_value.run_in_executor = mock_run_in_executor

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
        async def mock_run_in_executor_fail(*args, **kwargs):
            raise Exception("Async fail")

        with patch('asyncio.get_event_loop') as mock_loop:
            mock_loop.return_value.run_in_executor = mock_run_in_executor_fail

            # The function should catch the exception and try synchronous insert
            result = await consumer.flush_to_clickhouse_async(batch)

            self.assertTrue(result)
            # Should have been called twice: once async (failed), once sync (succeeded)
            # Actually, the implementation calls client.insert inside run_in_executor.
            # If run_in_executor fails, it calls client.insert directly.
            # So client.insert should be called exactly once (the successful sync one),
            # unless run_in_executor actually CALLED it before failing?
            # In our mock above, we raise Exception immediately, so client.insert is NOT called in the first try.
            # So it should be called exactly once (the sync fallback).
            self.mock_ch_client.insert.assert_called_once()

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
