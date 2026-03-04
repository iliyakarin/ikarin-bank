CREATE DATABASE IF NOT EXISTS banking_log;

CREATE TABLE IF NOT EXISTS banking_log.transactions (
    transaction_id String,
    sender_id Int64,
    recipient_email String,
    amount Float64,
    timestamp DateTime,
    status String
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (timestamp, transaction_id);
