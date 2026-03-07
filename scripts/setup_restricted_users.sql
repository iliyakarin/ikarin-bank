-- Create a restricted user for audit logging (logs ingestion)
-- This user should ONLY have permission to INSERT into the banking.transactions table (or activity log)

CREATE USER IF NOT EXISTS audit_logger IDENTIFIED WITH sha256_password BY 'secure_log_password_change_me';

-- Grant INSERT only on the specific table used for activity events
GRANT INSERT ON banking.transactions TO audit_logger;
GRANT INSERT ON banking.activity_events TO audit_logger;

-- If they need to check for anomalies (read access), we can grant SELECT on specific views or tables
-- But the requirement says "INSERT and SELECT (on specific views only)"
-- Let's assume we have a view for anomaly checking
GRANT SELECT ON banking.transactions_view TO audit_logger;

-- Revoke everything else
REVOKE ALL ON *.* FROM audit_logger;
GRANT USAGE ON *.* TO audit_logger;
GRANT INSERT ON banking.transactions TO audit_logger;
GRANT INSERT ON banking.activity_events TO audit_logger;
GRANT SELECT ON banking.transactions_view TO audit_logger;
