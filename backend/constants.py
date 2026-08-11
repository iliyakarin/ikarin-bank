"""Application-wide constants."""

# Subscription pricing (in cents)
SUBSCRIPTION_BLACK_PRICE = 4900  # $49.00/month

# Timeouts (in milliseconds)
KAFKA_REQUEST_TIMEOUT_MS = 10000
OPTIMAL_SESSION_TIMEOUT = 10000

# Sync check interval (in seconds)
CHECK_INTERVAL_SECONDS = 86400  # 24 hours

# E2E test seed balance (in cents)
E2E_SEED_BALANCE_CENTS = 100000  # $1000.00

# Transaction status/type/side
TRANSACTION_STATUS_PENDING = "pending"
TRANSACTION_TYPE_EXPENSE = "expense"
TRANSACTION_TYPE_TRANSFER = "transfer"
TRANSACTION_SIDE_DEBIT = "DEBIT"

# Contact type
CONTACT_TYPE_KARIN = "karin"

# Scheduled payment status - must match scheduled_payments_worker.py's query
SCHEDULED_PAYMENT_STATUS_ACTIVE = "Active"

# Outbox status - must match outbox_worker.py's query
OUTBOX_STATUS_PENDING = "pending"

# Activity log defaults
ACTIVITY_DETAILS_EMPTY = "{}"
NULL_UUID = "00000000-0000-0000-0000-000000000000"
