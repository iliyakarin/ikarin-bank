"""Tests for ClickHouse client thread-safety and batch flush synchronization."""
import pytest
import asyncio
from unittest.mock import MagicMock, patch
from clickhouse_utils import get_ch_client, _ch_lock
from handlers.message_handlers import flush_batch_to_clickhouse
from consumer import KafkaConsumerApp


@pytest.mark.asyncio
async def test_clickhouse_client_thread_safe_singleton():
    """Verify get_ch_client returns client safely under lock."""
    with patch("clickhouse_utils._create_ch_client") as mock_create:
        mock_client = MagicMock()
        mock_create.return_value = mock_client

        # Call get_ch_client concurrently from multiple coroutines
        async def fetch_client():
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, get_ch_client)

        results = await asyncio.gather(*(fetch_client() for _ in range(10)))
        for client in results:
            assert client == mock_client


@pytest.mark.asyncio
async def test_concurrent_flushes_execute_safely():
    """Verify concurrent flushes do not clash or throw concurrency errors."""
    mock_client = MagicMock()
    with patch("handlers.message_handlers.get_ch_client", return_value=mock_client):
        # Trigger two batch flushes simultaneously
        res1, res2 = await asyncio.gather(
            flush_batch_to_clickhouse("transactions", ["col1"], [["val1"]]),
            flush_batch_to_clickhouse("activity_events", ["col2"], [["val2"]]),
        )
        assert res1 is True
        assert res2 is True
        assert mock_client.insert.call_count == 2


@pytest.mark.asyncio
async def test_consumer_flush_all_sequential_success():
    """Verify consumer flush_all flushes tx and activity buffers sequentially and commits."""
    mock_client = MagicMock()
    with patch("handlers.message_handlers.get_ch_client", return_value=mock_client), \
         patch("consumer.Consumer") as mock_consumer_cls:
        
        mock_kafka_consumer = MagicMock()
        mock_consumer_cls.return_value = mock_kafka_consumer
        
        app = KafkaConsumerApp()
        app.tx_buffer = [{
            "transaction_id": "tx-1",
            "account_id": 1,
            "amount": 1000,
            "category": "Food",
            "merchant": "Cafe",
            "timestamp": "2026-08-21T10:00:00Z"
        }]
        app.activity_buffer = [{
            "event_id": "ev-1",
            "user_id": 1,
            "category": "security",
            "action": "login",
            "event_time": "2026-08-21T10:00:00Z",
            "title": "Logged in"
        }]
        
        await app.flush_all()
        
        assert len(app.tx_buffer) == 0
        assert len(app.activity_buffer) == 0
        mock_kafka_consumer.commit.assert_called_once()
