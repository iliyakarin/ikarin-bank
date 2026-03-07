"""
ClickHouse Migration Script — Activity Events Table
Run once to create the activity_events table without resetting existing data.
Usage: python migrate_clickhouse.py
"""
import os
import clickhouse_connect

CH_HOST = os.getenv("CLICKHOUSE_HOST")
CH_PORT = int(os.getenv("CLICKHOUSE_PORT", 8123))
CH_USER = os.getenv("CLICKHOUSE_USER")
CH_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD", "")


def run_migration():
    client = clickhouse_connect.get_client(
        host=CH_HOST, port=CH_PORT, username=CH_USER, password=CH_PASSWORD
    )

    print("🚀 Running ClickHouse migration...")

    # Ensure database exists
    client.command("CREATE DATABASE IF NOT EXISTS banking_log")

    # Create activity_events table
    client.command("""
        CREATE TABLE IF NOT EXISTS banking_log.activity_events (
            event_id        String,
            user_id         Int64,
            category        LowCardinality(String),
            action          LowCardinality(String),
            event_time      DateTime,
            title           String,
            details         String
        ) ENGINE = MergeTree()
        PARTITION BY toYYYYMM(event_time)
        ORDER BY (user_id, event_time, event_id)
    """)
    print("✅ Created banking_log.activity_events table")

    print("🎉 Migration complete!")


if __name__ == "__main__":
    run_migration()
