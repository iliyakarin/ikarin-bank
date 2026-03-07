-- Migration: Add Account Credentials fields to accounts table
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS routing_number VARCHAR(9);
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS account_number_encrypted VARCHAR(255);
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS account_number_last_4 VARCHAR(4);
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS internal_reference_id VARCHAR(100) UNIQUE;

CREATE INDEX IF NOT EXISTS idx_accounts_internal_ref ON accounts(internal_reference_id);
