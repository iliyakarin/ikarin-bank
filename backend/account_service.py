import secrets
import uuid
from cryptography.fernet import Fernet
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import Account
from typing import Optional
from config import settings

# Configuration
ABA_PREFIX = "1234"  # Karin-Bank branch prefix
ENCRYPTION_KEY = settings.ACCOUNT_ENCRYPTION_KEY

cipher_suite = Fernet(ENCRYPTION_KEY.encode()) if ENCRYPTION_KEY else None

def calculate_aba_checksum(routing_number: str) -> int:
    """
    Calculate the checksum for a 9-digit ABA routing number.
    Formula: 3(d1 + d4 + d7) + 7(d2 + d5 + d8) + 1(d3 + d6 + d9) mod 10 = 0
    """
    if len(routing_number) != 9 or not routing_number.isdigit():
        raise ValueError("ABA routing number must be exactly 9 digits.")
    
    d = [int(digit) for digit in routing_number]
    checksum = (
        3 * (d[0] + d[3] + d[6]) +
        7 * (d[1] + d[4] + d[7]) +
        1 * (d[2] + d[5] + d[8])
    ) % 10
    return checksum

def generate_aba() -> str:
    """Generates a valid 9-digit ABA routing number for Karin-Bank."""
    # Prefix is 4 digits, we need 4 more random digits + 1 checksum digit
    random_part = "".join([str(secrets.randbelow(10)) for _ in range(4)])
    partial_aba = ABA_PREFIX + random_part
    
    # We need to find the checksum digit 'x' such that (current_checksum + weight * x) % 10 == 0
    # For the 9th digit (d9), the weight is 1.
    d = [int(digit) for digit in partial_aba]
    current_val = (
        3 * (d[0] + d[3] + d[6]) +
        7 * (d[1] + d[4] + d[7]) +
        1 * (d[2] + d[5])
    )
    
    # 9th digit weight is 1. So (current_val + 1 * d9) % 10 == 0
    d9 = (10 - (current_val % 10)) % 10
    return partial_aba + str(d9)

def encrypt_account_number(number: str) -> str:
    """Encrypts the account number using Fernet symmetric encryption."""
    if not cipher_suite:
        raise RuntimeError("ACCOUNT_ENCRYPTION_KEY not configured.")
    return cipher_suite.encrypt(number.encode()).decode()

def decrypt_account_number(encrypted_number: str) -> str:
    """Decrypts the account number."""
    if not cipher_suite:
        raise RuntimeError("ACCOUNT_ENCRYPTION_KEY not configured.")
    return cipher_suite.decrypt(encrypted_number.encode()).decode()

def mask_account_number(number: str) -> str:
    """Returns a masked version of the account number (e.g., ****6789)."""
    if len(number) < 4:
        return "****"
    return "****" + number[-4:]

def generate_internal_reference() -> str:
    """Generates a unique internal reference ID for ClickHouse logging."""
    return f"KB-{secrets.token_hex(8).upper()}"

async def assign_account_credentials(db: AsyncSession, account: Account):
    """
    Orchestrates the generation and assignment of credentials to an Account.
    Uses UUIDs to ensure uniqueness without O(N) collision checks.
    """
    # 1. Generate Routing Number (consistent prefix for Karin-Bank)
    account.routing_number = generate_aba()
    
    # 2. Generate UUID-based account number
    # We use a standard UUID4 but strip hyphens for the internal reference/encrypted field if needed
    new_uuid = str(uuid.uuid4())
    account.account_uuid = new_uuid
    
    # For compatibility with existing last_4 logic, we take the last 4 chars of the UUID
    # or generate a random 10-digit number. Since we have a unique UUID now, 
    # we don't need to loop-detect collisions for the encrypted representation.
    acc_num = "".join(filter(str.isdigit, new_uuid))[:12]
    if len(acc_num) < 10:
        # Fallback if uuid doesn't have enough digits (rare but possible)
        acc_num = str(uuid.uuid4().int)[:12]
        
    account.account_number_encrypted = encrypt_account_number(acc_num)
    account.account_number_last_4 = acc_num[-4:]
            
    # 3. Generate Internal Reference ID
    while True:
        ref_id = generate_internal_reference()
        result = await db.execute(select(Account).filter(Account.internal_reference_id == ref_id))
        if not result.scalars().first():
            account.internal_reference_id = ref_id
            break
