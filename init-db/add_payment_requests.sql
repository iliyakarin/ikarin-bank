CREATE TABLE IF NOT EXISTS payment_requests (
    id SERIAL PRIMARY KEY,
    requester_id INTEGER NOT NULL REFERENCES users(id),
    target_email VARCHAR(100) NOT NULL,
    amount NUMERIC(15, 2) NOT NULL,
    purpose TEXT,
    status VARCHAR(50) NOT NULL DEFAULT 'pending_target',
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_payment_requests_requester_id ON payment_requests(requester_id);
CREATE INDEX idx_payment_requests_target_email ON payment_requests(target_email);

ALTER TABLE transactions ADD COLUMN IF NOT EXISTS commentary TEXT;
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS payment_request_id INTEGER REFERENCES payment_requests(id);
CREATE INDEX idx_transactions_payment_request_id ON transactions(payment_request_id);
