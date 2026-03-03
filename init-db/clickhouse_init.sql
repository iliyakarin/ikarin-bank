CREATE DATABASE IF NOT EXISTS banking;

CREATE TABLE IF NOT EXISTS banking.transactions (
    transaction_id UUID,
    account_id Int32,
    sender_email String DEFAULT '',
    recipient_email String DEFAULT '',
    amount Float64,
    category String,
    merchant String,
    transaction_type String DEFAULT 'expense',
    event_time DateTime64(3)
) ENGINE = ReplacingMergeTree()
ORDER BY (transaction_id);