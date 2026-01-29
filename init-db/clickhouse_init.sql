CREATE TABLE IF NOT EXISTS transactions (
    transaction_id UUID,
    account_id Int32,
    amount Float64,
    event_time DateTime64(3)
) ENGINE = ReplacingMergeTree()
ORDER BY (transaction_id);