CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE accounts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    balance DECIMAL(15, 2) DEFAULT 0.00
);

-- Transaction log in Postgres (Source of Truth)
CREATE TABLE transactions (
    id UUID PRIMARY KEY,
    account_id INTEGER REFERENCES accounts(id),
    amount DECIMAL(15, 2) NOT NULL,
    category VARCHAR(50),
    merchant VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);