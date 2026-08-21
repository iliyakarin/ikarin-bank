import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from routing_utils import (
    compute_routing_check_digit,
    validate_routing_number,
    get_district_from_routing,
    format_routing_number,
)

def test_compute_routing_check_digit_valid():
    # Chase NY (021000021) -> first 8 digits '02100002', check digit 1
    assert compute_routing_check_digit("02100002") == 1
    # BofA TX (111000012) -> first 8 digits '11100001', check digit 2
    assert compute_routing_check_digit("11100001") == 2
    # Karin Bank Node (123456780) -> first 8 digits '12345678', check digit 0
    assert compute_routing_check_digit("12345678") == 0
    # Karin Bank Branch (123400011) -> first 8 digits '12340001', check digit 1
    assert compute_routing_check_digit("12340001") == 1

def test_validate_routing_number_success():
    res = validate_routing_number("021000021")
    assert res["valid"] is True
    assert res["district_id"] == 2
    assert len(res["errors"]) == 0

def test_validate_routing_number_invalid_checksum():
    res = validate_routing_number("021000029")
    assert res["valid"] is False
    assert any("Invalid check digit" in err for err in res["errors"])

def test_validate_routing_number_invalid_length():
    res = validate_routing_number("123")
    assert res["valid"] is False
    assert any("Expected 9 digits" in err for err in res["errors"])

def test_get_district_from_routing():
    assert get_district_from_routing("021000021") == 2
    assert get_district_from_routing("121000248") == 12
    assert get_district_from_routing("111000012") == 11
    assert get_district_from_routing("011103093") == 1

def test_format_routing_number():
    assert format_routing_number("021000021") == "0210-00021"
