import os
import clickhouse_connect
import logging

logger = logging.getLogger(__name__)

# Configuration
CH_HOST = os.getenv("CLICKHOUSE_HOST", "localhost")
CH_PORT = int(os.getenv("CLICKHOUSE_PORT", 8123))
CH_USER = os.getenv("CLICKHOUSE_USER", "default")
CH_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD", "")
CH_DB = os.getenv("CLICKHOUSE_DB", "banking_log")

_ch_client = None

def get_ch_client():
    """Returns a singleton ClickHouse client instance."""
    global _ch_client
    if _ch_client is None:
        try:
            _ch_client = clickhouse_connect.get_client(
                host=CH_HOST,
                port=CH_PORT,
                username=CH_USER,
                password=CH_PASSWORD
            )
            logger.info("🚀 ClickHouse client connected successfully")
        except Exception as e:
            logger.error(f"❌ Failed to connect to ClickHouse: {e}")
            raise
    return _ch_client
