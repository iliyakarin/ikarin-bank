"""Pure ClickHouse query builders.

Each function returns (query_str, params_dict).  No user-supplied values are
interpolated into the SQL string; all go into the params dict so the
clickhouse-connect driver handles safe binding.

ClickHouse parameter syntax inside queries: {name:Type}
"""
from typing import Optional


def build_balance_history_query(
    ch_db: str,
    account_id: int,
    days: int,
) -> tuple[str, dict]:
    query = f"""
        SELECT toDate(event_time) as date, sum(amount) as daily_change
        FROM {ch_db}.transactions
        WHERE account_id = {{account_id:Int64}}
          AND event_time >= now() - toIntervalDay({{days:UInt32}})
        GROUP BY toDate(event_time)
        ORDER BY date
    """
    return query, {"account_id": account_id, "days": days}


def build_recent_transactions_query(
    ch_db: str,
    account_ids: list[int],
    hours: int,
) -> tuple[str, dict]:
    query = f"""
        SELECT toString(transaction_id), amount, category, merchant,
               transaction_type, transaction_side, event_time, status
        FROM {ch_db}.transactions
        WHERE account_id IN {{account_ids:Array(Int64)}}
          AND event_time >= now() - toIntervalHour({{hours:UInt32}})
        ORDER BY event_time DESC
        LIMIT 1 BY transaction_id
    """
    return query, {"account_ids": account_ids, "hours": hours}


def build_transactions_query(
    ch_db: str,
    account_ids: list[int],
    days: int,
    tx_type: Optional[str] = None,
    min_amount: Optional[int] = None,
    max_amount: Optional[int] = None,
    sort: str = "desc",
) -> tuple[str, dict]:
    params: dict = {"account_ids": account_ids, "days": days}
    conditions = [
        "account_id IN {account_ids:Array(Int64)}",
        "event_time >= now() - toIntervalDay({days:UInt32})",
    ]

    if tx_type == "incoming":
        conditions.append("amount > 0")
    elif tx_type == "outgoing":
        conditions.append("amount < 0")

    if min_amount is not None:
        conditions.append("abs(amount) >= {min_amount:Int64}")
        params["min_amount"] = min_amount * 100

    if max_amount is not None:
        conditions.append("abs(amount) <= {max_amount:Int64}")
        params["max_amount"] = max_amount * 100

    where_clause = " AND ".join(conditions)
    sort_dir = "ASC" if sort.lower() == "asc" else "DESC"

    query = f"""
        SELECT toString(transaction_id) as tx_id, sender_email, recipient_email,
               amount, category, merchant, event_time, status, transaction_type
        FROM {ch_db}.transactions
        WHERE {where_clause}
        ORDER BY event_time {sort_dir}
        LIMIT 1 BY transaction_id
    """
    return query, params
