from cryptography.fernet import Fernet
import secrets
import uuid
import logging
import datetime
from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from fastapi import HTTPException, status

from database import SessionLocal
from models.user import User
from models.account import Account
from models.transaction import Transaction
from models.management import Outbox
from config import settings
from activity import emit_activity

ABA_PREFIX = settings.ABA_PREFIX
ENCRYPTION_KEY = settings.ACCOUNT_ENCRYPTION_KEY
cipher_suite = Fernet(ENCRYPTION_KEY.encode()) if ENCRYPTION_KEY else None

def calculate_aba_checksum(routing_number: str) -> int:
    """Calculate the checksum for a 9-digit ABA routing number."""
    if len(routing_number) != 9 or not routing_number.isdigit():
        raise ValueError("ABA routing number must be exactly 9 digits.")
    d = [int(digit) for digit in routing_number]
    checksum = (3*(d[0]+d[3]+d[6]) + 7*(d[1]+d[4]+d[7]) + 1*(d[2]+d[5]+d[8])) % 10
    return checksum

def generate_aba() -> str:
    """Generates a valid 9-digit ABA routing number for Karin-Bank."""
    random_part = "".join([str(secrets.randbelow(10)) for _ in range(4)])
    partial = ABA_PREFIX + random_part
    d = [int(digit) for digit in partial]
    current = (3*(d[0]+d[3]+d[6]) + 7*(d[1]+d[4]+d[7]) + 1*(d[2]+d[5]))
    d9 = (10 - (current % 10)) % 10
    return partial + str(d9)

def encrypt_account_number(number: str) -> str:
    if not cipher_suite: raise RuntimeError("ENCRYPTION_KEY missing")
    return cipher_suite.encrypt(number.encode()).decode()

def decrypt_account_number(encrypted_number: str) -> str:
    if not cipher_suite: raise RuntimeError("ENCRYPTION_KEY missing")
    return cipher_suite.decrypt(encrypted_number.encode()).decode()

def mask_account_number(number: str) -> str:
    if len(number) < 4: return "****"
    return "****" + number[-4:]

async def assign_account_credentials(db: AsyncSession, account: Account):
    """Generate and assign ABA and encrypted account number."""
    account.routing_number = generate_aba()
    new_uuid = str(uuid.uuid4())
    account.account_uuid = new_uuid
    acc_num = "".join(filter(str.isdigit, new_uuid))[:12]
    if len(acc_num) < 10: acc_num = str(uuid.uuid4().int)[:12]
    account.account_number_encrypted = encrypt_account_number(acc_num)
    account.account_number_last_4 = acc_num[-4:]
    
    while True:
        ref = f"KB-{secrets.token_hex(8).upper()}"
        res = await db.execute(select(Account).where(Account.internal_reference_id == ref))
        if not res.scalars().first():
            account.internal_reference_id = ref
            break

async def create_user_sub_account(db: AsyncSession, user_id: int, name: str, client_ip: str, user_agent: str):
    """Create a sub-account with limit check."""
    res = await db.execute(select(func.count(Account.id)).where(Account.user_id == user_id, Account.is_main == False))
    count = res.scalar() or 0
    if count >= 10: raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Maximum of 10 sub-accounts reached")

    res = await db.execute(select(Account).where(Account.user_id == user_id, Account.is_main == True))
    main = res.scalars().first()
    if not main: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Main account not found")

    new_sub = Account(user_id=user_id, is_main=False, parent_account_id=main.id, name=name, balance=0, reserved_balance=0)
    await assign_account_credentials(db, new_sub)
    db.add(new_sub)
    emit_activity(db, user_id, "sub_account", "created", f"Created sub-account '{name}'", {"name": name}, ip=client_ip, user_agent=user_agent)
    await db.commit()
    await db.refresh(new_sub)
    return new_sub

async def execute_internal_transfer(
    db: AsyncSession, user_id: int, from_id: int, to_id: int,
    amount: int, comm: Optional[str], ip: str, ua: str, email: str
):
    """Atomic internal transfer between user accounts."""
    if amount <= 0: raise HTTPException(status_code=400, detail="Amount must be > 0")
    if from_id == to_id: raise HTTPException(status_code=400, detail="Cannot transfer to same account")

    ids = sorted([from_id, to_id])
    res = await db.execute(select(Account).where(Account.id.in_(ids), Account.user_id == user_id).with_for_update())
    accounts = res.scalars().all()
    acc_map = {a.id: a for a in accounts}
    sender, receiver = acc_map.get(from_id), acc_map.get(to_id)

    if not sender or not receiver: raise HTTPException(status_code=404, detail="Accounts not found")
    if sender.balance < amount: raise HTTPException(status_code=400, detail="Insufficient funds in source account")

    sender.balance -= amount
    receiver.balance += amount
    parent = str(uuid.uuid4())
    
    db.add(Transaction(
        id=str(uuid.uuid4()), parent_id=parent, account_id=sender.id, amount=-amount,
        category="Internal Transfer", merchant=f"To {receiver.name}", status="cleared",
        transaction_type="transfer", transaction_side="DEBIT", internal_account_last_4=sender.account_number_last_4,
        sender_email=email, recipient_email=email, commentary=comm
    ))
    db.add(Transaction(
        id=str(uuid.uuid4()), parent_id=parent, account_id=receiver.id, amount=amount,
        category="Internal Transfer", merchant=f"From {sender.name}", status="cleared",
        transaction_type="transfer", transaction_side="CREDIT", internal_account_last_4=receiver.account_number_last_4,
        sender_email=email, recipient_email=email, commentary=comm
    ))
    
    emit_activity(db, user_id, "sub_account", "transfer", f"Transferred {amount/100:.2f} to {receiver.name}", {"amount": amount}, ip=ip, user_agent=ua)
    await db.commit()
    return sender, receiver
