
import pytest
from unittest.mock import MagicMock, patch, mock_open, AsyncMock
import json
import asyncio
from datetime import datetime
import os
import sys

# Ensure backend is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture
def mock_consumer_deps():
    mock_ch_client = MagicMock()
    mock_kafka = MagicMock()

    modules_to_patch = {
        'confluent_kafka': mock_kafka,
        'clickhouse_connect': MagicMock()
    }

    with patch.dict(sys.modules, modules_to_patch):
        import consumer
        # Force the mocks into the consumer module
        consumer.get_ch_client = MagicMock(return_value=mock_ch_client)
        consumer.get_clickhouse_client = MagicMock(return_value=mock_ch_client)
        consumer.ch_client = mock_ch_client
        yield consumer, mock_ch_client

@pytest.mark.asyncio
async def test_flush_to_clickhouse_async_success(mock_consumer_deps):
    """Test successful async flush to ClickHouse"""
    consumer, mock_ch_client = mock_consumer_deps
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

    with patch('consumer.asyncio.get_event_loop', return_value=mock_loop):
        result = await consumer.flush_to_clickhouse_async(batch)

    assert result is True
    assert mock_ch_client.insert.call_count == 1

    # Verify correct table and columns
    args, kwargs = mock_ch_client.insert.call_args
    assert args[0].endswith(".transactions")
    assert "transaction_id" in kwargs['column_names']

@pytest.mark.asyncio
async def test_flush_to_clickhouse_async_failure_fallback(mock_consumer_deps):
    """Test fallback to sync flush if async fails"""
    consumer, mock_ch_client = mock_consumer_deps
    batch = [{"transaction_id": "tx1", "account_id": 1, "amount": 100, "category": "cat", "merchant": "merch", "timestamp": "2023-01-01"}]

    # Make async call fail (first call is in executor)
    mock_ch_client.insert.side_effect = [Exception("Async fail"), None]

    mock_loop = MagicMock()
    mock_loop.run_in_executor = AsyncMock(side_effect=lambda exec, f, *a: f(*a))

    with patch('consumer.asyncio.get_event_loop', return_value=mock_loop):
        result = await consumer.flush_to_clickhouse_async(batch)

    assert result is True
    # Should be called once in executor (failed) and once as fallback
    assert mock_ch_client.insert.call_count == 2

def test_log_malformed_message_batch(mock_consumer_deps):
    """Test DLQ logging"""
    consumer, _ = mock_consumer_deps
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
        assert "bad_json" in content
        assert "err" in content
