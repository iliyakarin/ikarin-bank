import pytest
import datetime
from v2.banking.aba_validator import ABAValidator

def test_aba_checksum_valid():
    # Valid ABA number
    assert ABAValidator.validate_checksum("123456780") is True

def test_aba_checksum_invalid():
    # Invalid ABA number (checksum will not be 0 mod 10)
    assert ABAValidator.validate_checksum("123456789") is False

def test_aba_format_validation():
    assert ABAValidator.validate_format("123456789") is True
    assert ABAValidator.validate_format("12345") is False
    assert ABAValidator.validate_format("abc") is False
