CREATE DATABASE IF NOT EXISTS banking_log;

CREATE TABLE IF NOT EXISTS banking_log.transactions (
    transaction_id String,
    sender_id Int64,
    recipient_email String,
    amount Float64,
    timestamp DateTime,
    status String
) ENGINE = ReplacingMergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (timestamp, transaction_id);

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
