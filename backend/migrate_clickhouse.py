"""
ClickHouse Migration Script — Activity Events Table
Run once to create the activity_events table without resetting existing data.
Usage: python migrate_clickhouse.py
"""
import os
import clickhouse_connect

CH_HOST = os.getenv("CLICKHOUSE_HOST", "localhost")
CH_PORT = int(os.getenv("CLICKHOUSE_PORT", 8123))
CH_USER = os.getenv("CLICKHOUSE_USER", "default")
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

    # Migrate transactions table if it exists, or create it
    print("🛠️ Migrating transactions table schema...")
    client.command(f"CREATE DATABASE IF NOT EXISTS {os.getenv('CLICKHOUSE_DB', 'banking_log')}")
    
    # Check if table exists
    table_exists = client.command(f"EXISTS TABLE {os.getenv('CLICKHOUSE_DB', 'banking_log')}.transactions")
    
    if table_exists:
        # Add missing columns
        client.command(f"""
            ALTER TABLE {os.getenv('CLICKHOUSE_DB', 'banking_log')}.transactions 
            ADD COLUMN IF NOT EXISTS parent_id Nullable(String),
            ADD COLUMN IF NOT EXISTS account_id Int64,
            ADD COLUMN IF NOT EXISTS sender_email Nullable(String),
            ADD COLUMN IF NOT EXISTS merchant String,
            ADD COLUMN IF NOT EXISTS transaction_type String,
            ADD COLUMN IF NOT EXISTS transaction_side String,
            ADD COLUMN IF NOT EXISTS event_time DateTime DEFAULT now(),
            ADD COLUMN IF NOT EXISTS category String,
            ADD COLUMN IF NOT EXISTS internal_account_last_4 Nullable(String)
        """)
        # If timestamp exists but event_time is new, we might want to sync them, 
        # but DEFAULT now() is a safe fallback for new columns.
        print("✅ Altered banking_log.transactions table (added missing columns)")
    else:
        client.command(f"""
            CREATE TABLE {os.getenv('CLICKHOUSE_DB', 'banking_log')}.transactions (
                transaction_id String,
                parent_id Nullable(String),
                account_id Int64,
                sender_email Nullable(String),
                recipient_email Nullable(String),
                amount Float64,
                category String,
                merchant String,
                transaction_type String,
                transaction_side String,
                event_time DateTime,
                internal_account_last_4 Nullable(String),
                status String
            ) ENGINE = ReplacingMergeTree()
            PARTITION BY toYYYYMM(event_time)
            ORDER BY (account_id, event_time, transaction_id)
        """)
        print("✅ Created banking_log.transactions table")

    print("🎉 Migration complete!")


if __name__ == "__main__":
    run_migration()
