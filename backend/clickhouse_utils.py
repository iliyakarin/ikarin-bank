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
