CREATE DATABASE IF NOT EXISTS banking_log;

CREATE TABLE IF NOT EXISTS banking_log.transactions (
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
ORDER BY (account_id, event_time, transaction_id);

CREATE TABLE IF NOT EXISTS banking_log.activity_events (
    event_id        String,
    user_id         Int64,
    category        LowCardinality(String),
    action          LowCardinality(String),
    event_time      DateTime,
    title           String,
    details         String
) ENGINE = ReplacingMergeTree()
PARTITION BY toYYYYMM(event_time)
ORDER BY (user_id, event_time, event_id);
