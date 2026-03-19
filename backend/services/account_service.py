from cryptography.fernet import Fernet
import secrets
import uuid
import logging
import re
import datetime
from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException

from database import Account, Transaction, Outbox, User
from config import settings
from activity import emit_activity

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
    new_uuid = str(uuid.uuid4())
    account.account_uuid = new_uuid

    acc_num = "".join(filter(str.isdigit, new_uuid))[:12]
    if len(acc_num) < 10:
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

async def create_user_sub_account(db: AsyncSession, user_id: int, name: str, client_ip: str, user_agent: str):
    """Handles sub-account creation logic and activity emission."""
    from sqlalchemy import func

    # Check constraint: max 10 sub-accounts
    result = await db.execute(select(func.count(Account.id)).filter(
        Account.user_id == user_id,
        Account.is_main == False
    ))
    sub_account_count = result.scalar()

    if sub_account_count >= 10:
        raise HTTPException(status_code=400, detail="Maximum of 10 sub-accounts reached")

    # Find the main account to link as parent
    result = await db.execute(select(Account).filter(
        Account.user_id == user_id,
        Account.is_main == True
    ))
    main_account = result.scalars().first()

    if not main_account:
        raise HTTPException(status_code=404, detail="Main account not found")

    new_sub = Account(
        user_id=user_id,
        is_main=False,
        parent_account_id=main_account.id,
        name=name,
        balance=0,
        reserved_balance=0
    )
    await assign_account_credentials(db, new_sub)
    db.add(new_sub)

    emit_activity(
        db, user_id, "sub_account", "created", f"Created sub-account '{name}'",
        {"name": name, "sub_count": sub_account_count + 1},
        ip=client_ip, user_agent=user_agent
    )
    await db.commit()
    await db.refresh(new_sub)
    return new_sub

async def execute_internal_transfer(
    db: AsyncSession, user_id: int, from_account_id: int, to_account_id: int,
    amount: int, commentary: Optional[str], client_ip: str, user_agent: str, user_email: str
):
    """Handles internal transfer between a user's own accounts."""
    if amount <= 0:
         raise HTTPException(status_code=400, detail="Transfer amount must be positive")

    if from_account_id == to_account_id:
        raise HTTPException(status_code=400, detail="Cannot transfer to the same account")

    first_id, second_id = sorted([from_account_id, to_account_id])

    res1 = await db.execute(select(Account).filter(Account.id == first_id, Account.user_id == user_id).with_for_update())
    acc1 = res1.scalars().first()
    res2 = await db.execute(select(Account).filter(Account.id == second_id, Account.user_id == user_id).with_for_update())
    acc2 = res2.scalars().first()

    if not acc1 or not acc2:
         raise HTTPException(status_code=404, detail="One or more accounts not found")

    if first_id == from_account_id:
         sender = acc1
         receiver = acc2
    else:
         sender = acc2
         receiver = acc1

    if sender.balance < amount:
         raise HTTPException(status_code=400, detail="Insufficient funds")

    sender.balance -= amount
    receiver.balance += amount

    tx_id_parent = str(uuid.uuid4())

    sender_tx = Transaction(
        id=str(uuid.uuid4()), parent_id=tx_id_parent, account_id=sender.id,
        amount=-amount, category="Internal Transfer", merchant=f"Transfer to {receiver.name}",
        status="cleared", transaction_type="transfer", transaction_side="DEBIT",
        commentary=commentary, internal_account_last_4=sender.account_number_last_4,
        sender_email=user_email, recipient_email=user_email
    )

    receiver_tx = Transaction(
        id=str(uuid.uuid4()), parent_id=tx_id_parent, account_id=receiver.id,
        amount=amount, category="Internal Transfer", merchant=f"Transfer from {sender.name}",
        status="cleared", transaction_type="transfer", transaction_side="CREDIT",
        commentary=commentary, internal_account_last_4=receiver.account_number_last_4,
        sender_email=user_email, recipient_email=user_email
    )

    db.add(sender_tx)
    db.add(receiver_tx)

    emit_activity(
        db, user_id, "sub_account", "transfer",
        f"Transferred {amount / 100:.2f} from {sender.name} to {receiver.name}",
        {"from_account": sender.name, "to_account": receiver.name, "amount": amount, "transaction_id": tx_id_parent},
        ip=client_ip, user_agent=user_agent
    )

    await db.commit()
    return sender, receiver
