import asyncio
import clickhouse_connect
import logging
import threading
from typing import Optional, List, Any, Dict
from config import settings

logger = logging.getLogger(__name__)

# Configuration
CH_HOST = settings.CLICKHOUSE_HOST
CH_PORT = settings.CLICKHOUSE_PORT
CH_USER = settings.CLICKHOUSE_USER
CH_PASSWORD = settings.CLICKHOUSE_PASSWORD
CH_DB = settings.CLICKHOUSE_DB

_ch_client = None
_ch_lock = threading.RLock()


def get_ch_client():
    """Returns a ClickHouse client instance with reconnect logic.

    Thread-safe client getter.
    """
    global _ch_client
    with _ch_lock:
        if _ch_client is None:
            _ch_client = _create_ch_client()
            return _ch_client

        # Health check: try a lightweight query to verify the connection is alive
        try:
            _ch_client.command("SELECT 1")
            return _ch_client
        except Exception as e:
            logger.warning(f"ClickHouse connection health check failed: {e}. Reconnecting...")
            _ch_client = None
            _ch_client = _create_ch_client()
            return _ch_client


def _create_ch_client():
    """Create a new ClickHouse client instance."""
    try:
        client = clickhouse_connect.get_client(
            host=CH_HOST,
            port=CH_PORT,
            username=CH_USER,
            password=CH_PASSWORD,
        )
        logger.info("ClickHouse client connected successfully")
        return client
    except Exception as e:
        logger.error(f"Failed to connect to ClickHouse: {e}")
        raise


async def execute_ch_query(query: str, parameters: Optional[dict] = None, client_getter=None):
    """Executes a query asynchronously in a threadpool executor under the client lock."""
    getter = client_getter or get_ch_client
    def _run():
        with _ch_lock:
            client = getter()
            return client.query(query, parameters=parameters)

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _run)


async def execute_ch_command(command: str, parameters: Optional[dict] = None, client_getter=None):
    """Executes a command asynchronously in a threadpool executor under the client lock."""
    getter = client_getter or get_ch_client
    def _run():
        with _ch_lock:
            client = getter()
            return client.command(command, parameters=parameters)

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _run)


async def execute_ch_insert(table: str, data: list, column_names: list, client_getter=None):
    """Executes a batch insert asynchronously in a threadpool executor under the client lock."""
    getter = client_getter or get_ch_client
    def _run():
        with _ch_lock:
            client = getter()
            return client.insert(f"{CH_DB}.{table}", data, column_names=column_names)

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _run)


