import pytest
from account_service import calculate_aba_checksum, generate_aba, generate_account_number, encrypt_account_number, decrypt_account_number, mask_account_number
import secrets

def test_aba_checksum_validation():
    # Valid ABA routing number (Chase Manhattan Bank)
    valid_aba = "021000021"
    # 3(0+0+0) + 7(2+0+2) + 1(1+0+1) = 0 + 28 + 2 = 30; 30 % 10 = 0
    assert calculate_aba_checksum(valid_aba) == 0
    
    # Invalid ABA
    invalid_aba = "021000022"
    assert calculate_aba_checksum(invalid_aba) != 0

def test_generate_aba():
    for _ in range(100):
        aba = generate_aba()
        assert len(aba) == 9
        assert aba.startswith("1234")
        assert calculate_aba_checksum(aba) == 0

def test_generate_account_number():
    numbers = set()
    for _ in range(1000):
        acc_num = generate_account_number()
        assert 10 <= len(acc_num) <= 12
        assert acc_num.isdigit()
        assert acc_num[0] != "0"
        numbers.add(acc_num)
    
    # Check for uniqueness in a small sample (entropy check)
    assert len(numbers) == 1000

def test_encryption_roundtrip():
    original = "123456789012"
    encrypted = encrypt_account_number(original)
    assert encrypted != original
    decrypted = decrypt_account_number(encrypted)
    assert decrypted == original

def test_mask_account_number():
    assert mask_account_number("1234567890") == "****7890"
    assert mask_account_number("123") == "****"
    assert mask_account_number("12345") == "****2345"
