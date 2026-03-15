import pytest
from backend.money_utils import to_cents, from_cents

def test_to_cents():
    assert to_cents("10.00") == 1000
    assert to_cents("10.05") == 1005
    assert to_cents(1000) == 1000
    assert to_cents("0.01") == 1
    assert to_cents("0") == 0
    assert to_cents("-10.00") == -1000
    assert to_cents("-0.01") == -1
    
    # Test invalid inputs
    with pytest.raises(ValueError):
        to_cents(10.05)  # Can't pass float directly anymore
    with pytest.raises(ValueError):
        to_cents("abc")

def test_from_cents():
    assert from_cents(1000) == "10.00"
    assert from_cents(1005) == "10.05"
    assert from_cents(1) == "0.01"
    assert from_cents(0) == "0.00"
    assert from_cents(-1000) == "-10.00"
    assert from_cents(-1) == "-0.01"
