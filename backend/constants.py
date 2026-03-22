"""Shared constants and defaults for the KarinBank backend.

This module provides a centralized location for magic strings, default values,
and enumeration-like constants used across the application to avoid hardcoding
and ensure consistency.
"""

# UUIDs
NULL_UUID = "00000000-0000-0000-0000-000000000000"

# Transaction Constants
TRANSACTION_TYPE_EXPENSE = "expense"
TRANSACTION_TYPE_INCOME = "income"
TRANSACTION_TYPE_TRANSFER = "transfer"
TRANSACTION_TYPE_P2P = "p2p"

TRANSACTION_STATUS_PENDING = "pending"
TRANSACTION_STATUS_COMPLETED = "completed"
TRANSACTION_STATUS_FAILED = "failed"
TRANSACTION_STATUS_CANCELLED = "cancelled"

TRANSACTION_SIDE_DEBIT = "DEBIT"
TRANSACTION_SIDE_CREDIT = "CREDIT"

# Activity Constants
ACTIVITY_DETAILS_EMPTY = "{}"

# Scheduled Payment Constants
SCHEDULED_PAYMENT_STATUS_ACTIVE = "Active"
SCHEDULED_PAYMENT_STATUS_PAUSED = "Paused"
SCHEDULED_PAYMENT_STATUS_COMPLETED = "Completed"

# Contact Constants
CONTACT_TYPE_KARIN = "karin"
CONTACT_TYPE_EXTERNAL = "external"

# Outbox Constants
OUTBOX_STATUS_PENDING = "pending"
OUTBOX_STATUS_PROCESSED = "processed"
OUTBOX_STATUS_FAILED = "failed"
