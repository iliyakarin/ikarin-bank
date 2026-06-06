import clickhouse_connect
import logging
from config import settings

logger = logging.getLogger(__name__)

# Configuration
CH_HOST = settings.CLICKHOUSE_HOST
CH_PORT = settings.CLICKHOUSE_PORT
CH_USER = settings.CLICKHOUSE_USER
CH_PASSWORD = settings.CLICKHOUSE_PASSWORD
CH_DB = settings.CLICKHOUSE_DB

_ch_client = None


def get_ch_client():
    """Returns a ClickHouse client instance with reconnect logic.

    Returns a singleton client. If the client becomes unresponsive,
    it is recreated on the next call.
    """
    global _ch_client
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
