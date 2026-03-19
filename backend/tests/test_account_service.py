import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.account_service import calculate_aba_checksum, generate_aba, encrypt_account_number, decrypt_account_number, mask_account_number
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

import pytest
from database import Account
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import AsyncMock, MagicMock
from services.account_service import assign_account_credentials

@pytest.mark.asyncio
async def test_assign_account_credentials():
    # Mock AsyncSession
    db = AsyncMock(spec=AsyncSession)

    # Setup mock result
    mock_scalars = MagicMock()
    mock_scalars.first.return_value = None

    mock_result = MagicMock()
    mock_result.scalars.return_value = mock_scalars

    # db.execute is awaited, so it returns mock_result
    db.execute.return_value = mock_result

    account = Account()
    await assign_account_credentials(db, account)

    assert account.routing_number.startswith("1234")
    assert len(account.routing_number) == 9
    assert account.account_uuid is not None
    assert account.account_number_encrypted is not None
    assert len(account.account_number_last_4) == 4
    assert account.internal_reference_id.startswith("KB-")

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
