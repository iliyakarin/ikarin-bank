import pytest
import datetime
from decimal import Decimal
import sys
import os

# Add parent directory to path to import main
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from main import _calculate_next_run_at, ScheduledTransferCreate

def test_calculate_next_run_at_daily():
    start = datetime.datetime(2026, 1, 1, 10, 0)
    result = _calculate_next_run_at(start, "Daily")
    assert result == start + datetime.timedelta(days=1)

def test_calculate_next_run_at_weekly():
    start = datetime.datetime(2026, 1, 1, 10, 0)
    result = _calculate_next_run_at(start, "Weekly")
    assert result == start + datetime.timedelta(weeks=1)

def test_calculate_next_run_at_monthly():
    # Regular month
    start = datetime.datetime(2026, 1, 15, 10, 0)
    result = _calculate_next_run_at(start, "Monthly")
    assert result == datetime.datetime(2026, 2, 15, 10, 0)

    # Month end boundary
    start = datetime.datetime(2026, 1, 31, 10, 0)
    result = _calculate_next_run_at(start, "Monthly")
    assert result == datetime.datetime(2026, 2, 28, 10, 0)

def test_calculate_next_run_at_specific_day():
    # 2026-03-06 is a Friday
    start = datetime.datetime(2026, 3, 6, 10, 0)

    # Next Monday should be 2026-03-09
    result = _calculate_next_run_at(start, "Specific Day of Week", "Monday")
    assert result == datetime.datetime(2026, 3, 9, 10, 0)

    # Next Friday (since today is Friday, it should be next week)
    result = _calculate_next_run_at(start, "Specific Day of Week", "Friday")
    assert result == datetime.datetime(2026, 3, 13, 10, 0)

def test_calculate_next_run_at_specific_date():
    start = datetime.datetime(2026, 1, 15, 10, 0)

    # Next 25th of the month
    result = _calculate_next_run_at(start, "Specific Date of Month", "25")
    assert result == datetime.datetime(2026, 2, 25, 10, 0)

    # Next 31st of the month (Feb only has 28 in 2026)
    result = _calculate_next_run_at(start, "Specific Date of Month", "31")
    assert result == datetime.datetime(2026, 2, 28, 10, 0)

def test_calculate_next_run_at_one_time():
    start = datetime.datetime(2026, 1, 1, 10, 0)
    result = _calculate_next_run_at(start, "One-time")
    assert result is None

def test_pydantic_schema_validation_valid():
    """
    Tests that a valid dictionary can be parsed into the ScheduledTransferCreate schema.
    """
    data = {
        "recipient_email": "vendor@test.com",
        "amount": 500.00,
        "frequency": "Specific Date of Month",
        "frequency_interval": "15",
        "start_date": "2026-05-15T12:00:00Z",
        "end_condition": "Number of Payments",
        "target_payments": 12,
        "reserve_amount": True
    }

    schema = ScheduledTransferCreate(**data)

    assert schema.recipient_email == "vendor@test.com"
    assert schema.amount == Decimal("500.00")
    assert schema.frequency == "Specific Date of Month"
    assert schema.frequency_interval == "15"
    assert schema.end_condition == "Number of Payments"
    assert schema.target_payments == 12
    assert schema.reserve_amount is True
    assert schema.end_date is None

def test_pydantic_schema_validation_minimal():
    """
    Tests the schema with only required fields.
    """
    data = {
        "recipient_email": "user@test.com",
        "amount": 10.00,
        "frequency": "One-time",
        "start_date": "2026-01-01T00:00:00Z",
        "end_condition": "Until Cancelled"
    }

    schema = ScheduledTransferCreate(**data)

    assert schema.recipient_email == "user@test.com"
    assert schema.reserve_amount is False
    assert schema.target_payments is None
