-- Create a restricted user for audit logging (logs ingestion)
-- This user should ONLY have permission to INSERT into the banking.transactions table (or activity log)

CREATE USER IF NOT EXISTS ${AUDIT_LOGGER_USER} IDENTIFIED WITH sha256_password BY '${AUDIT_LOGGER_PASSWORD}';

-- Grant INSERT only on the specific table used for activity events
GRANT INSERT ON banking_log.transactions TO ${AUDIT_LOGGER_USER};
GRANT INSERT ON banking_log.activity_events TO ${AUDIT_LOGGER_USER};

-- If they need to check for anomalies (read access), we can grant SELECT on specific views or tables
-- But the requirement says "INSERT and SELECT (on specific views only)"
-- Let's assume we have a view for anomaly checking
GRANT SELECT ON banking_log.transactions_view TO ${AUDIT_LOGGER_USER};

-- Revoke everything else
REVOKE ALL ON *.* FROM ${AUDIT_LOGGER_USER};
GRANT USAGE ON *.* TO ${AUDIT_LOGGER_USER};
GRANT INSERT ON banking_log.transactions TO ${AUDIT_LOGGER_USER};
GRANT INSERT ON banking_log.activity_events TO ${AUDIT_LOGGER_USER};
GRANT SELECT ON banking_log.transactions_view TO ${AUDIT_LOGGER_USER};
