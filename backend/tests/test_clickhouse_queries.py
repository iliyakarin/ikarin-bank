"""Tests for ClickHouse query builders.

Behaviour under test: every user-supplied value (account IDs, time ranges,
amounts) must appear in the params dict — never interpolated into the SQL
string.  A query string containing a raw user value is injectable.
"""
import pytest
from clickhouse_queries import (
    build_balance_history_query,
    build_recent_transactions_query,
    build_transactions_query,
)

CH_DB = "karin_bank"


# ---------------------------------------------------------------------------
# build_balance_history_query
# ---------------------------------------------------------------------------

def test_balance_history_account_id_not_in_query_string():
    query, params = build_balance_history_query(CH_DB, account_id=99, days=30)
    assert "99" not in query


def test_balance_history_days_not_in_query_string():
    query, params = build_balance_history_query(CH_DB, account_id=99, days=30)
    # 30 must not appear as a bare integer literal in the SQL
    assert " 30 " not in query and " 30\n" not in query and "=30" not in query


def test_balance_history_params_carry_values():
    query, params = build_balance_history_query(CH_DB, account_id=99, days=30)
    assert params["account_id"] == 99
    assert params["days"] == 30


def test_balance_history_query_references_db():
    query, _ = build_balance_history_query(CH_DB, account_id=1, days=7)
    assert CH_DB in query


# ---------------------------------------------------------------------------
# build_recent_transactions_query
# ---------------------------------------------------------------------------

def test_recent_transactions_ids_not_interpolated():
    query, params = build_recent_transactions_query(CH_DB, account_ids=[1, 2, 3], hours=24)
    # The literal comma-joined string must not appear
    assert "1,2,3" not in query


def test_recent_transactions_hours_not_in_query_string():
    query, params = build_recent_transactions_query(CH_DB, account_ids=[5], hours=48)
    assert "48" not in query


def test_recent_transactions_params_carry_values():
    query, params = build_recent_transactions_query(CH_DB, account_ids=[7, 8], hours=12)
    assert params["account_ids"] == [7, 8]
    assert params["hours"] == 12


# ---------------------------------------------------------------------------
# build_transactions_query
# ---------------------------------------------------------------------------

def test_transactions_ids_not_interpolated():
    query, params = build_transactions_query(CH_DB, account_ids=[10, 20], days=7)
    assert "10,20" not in query


def test_transactions_days_not_in_query_string():
    query, params = build_transactions_query(CH_DB, account_ids=[1], days=14)
    assert "14" not in query


def test_transactions_params_carry_base_values():
    query, params = build_transactions_query(CH_DB, account_ids=[3], days=7)
    assert params["account_ids"] == [3]
    assert params["days"] == 7


def test_transactions_min_amount_not_interpolated():
    query, params = build_transactions_query(
        CH_DB, account_ids=[1], days=7, min_amount=100
    )
    # 100 * 100 = 10000 — must not appear as a literal in SQL
    assert "10000" not in query
    assert params["min_amount"] == 10000


def test_transactions_max_amount_not_interpolated():
    query, params = build_transactions_query(
        CH_DB, account_ids=[1], days=7, max_amount=500
    )
    assert "50000" not in query
    assert params["max_amount"] == 50000


def test_transactions_no_amount_filters_absent_from_params():
    _, params = build_transactions_query(CH_DB, account_ids=[1], days=7)
    assert "min_amount" not in params
    assert "max_amount" not in params
