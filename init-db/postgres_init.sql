CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
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
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Seed data
INSERT INTO users (first_name, last_name, email, password_hash) VALUES 
('Iliya', 'Karin', 'ikarin@example.com', '$2b$12$/VohZlBcVbRcK1VHOXr5.eQMIwvO80BvojvneaWq9UOiLkOjnKNGG'), -- password123
('Admin', 'User', 'ikarin@admin.com', '$2b$12$/VohZlBcVbRcK1VHOXr5.eQMIwvO80BvojvneaWq9UOiLkOjnKNGG'),   -- password123
('Admin', 'User2', 'ikarin2@admin.com', '$2b$12$6PGHyME92AS7UE4m/KJsr.NCK772r5tFd7xDwT/ODAy3MveSeaxEW'); -- password321

INSERT INTO accounts (user_id, balance) VALUES 
(1, 64230.15),
(2, 10000.00),
(3, 2500.00);