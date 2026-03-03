-- Migration: Add ScheduledPayment table and reserved_balance to Account
ALTER TABLE accounts ADD COLUMN reserved_balance NUMERIC(15, 2) DEFAULT 0.00;

CREATE TABLE scheduled_payments (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    recipient_email VARCHAR(100) NOT NULL,
    amount NUMERIC(15, 2) NOT NULL,
    frequency VARCHAR(50) NOT NULL,
    frequency_interval VARCHAR(50),
    start_date TIMESTAMP NOT NULL,
    end_condition VARCHAR(50) NOT NULL,
    end_date TIMESTAMP,
    target_payments INTEGER,
    payments_made INTEGER NOT NULL DEFAULT 0,
    next_run_at TIMESTAMP,
    status VARCHAR(20) NOT NULL DEFAULT 'Active',
    idempotency_key VARCHAR(100) NOT NULL UNIQUE,
    reserve_amount BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX ix_scheduled_payments_user_id ON scheduled_payments(user_id);
CREATE INDEX ix_scheduled_payments_next_run_at ON scheduled_payments(next_run_at);
