from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from pydantic import BaseModel
from typing import Optional, List
import re

from database import Account, User, Transaction, SessionLocal
from activity import emit_activity
from services.account_service import (
    assign_account_credentials,
    decrypt_account_number,
    mask_account_number,
    create_user_sub_account,
    execute_internal_transfer,
)
from auth_utils import get_db, get_current_user
from money_utils import from_cents

router = APIRouter(prefix="/accounts", tags=["accounts"])

# --- Schemas ---
class SubAccountCreate(BaseModel):
    name: str

class SubAccountRename(BaseModel):
    name: str

class InternalTransferRequest(BaseModel):
    from_account_id: int
    to_account_id: int
    amount: int
    commentary: Optional[str] = None

# --- Helpers ---
def is_valid_name(name: str) -> bool:
    """Minimal validation for account names."""
    return bool(re.match(r"^[a-zA-Z0-9 ]+$", name))

async def check_account_owner(account_id: int, user_id: int, db: AsyncSession) -> Account:
    """Ensures an account exists and belongs to the specified user."""
    result = await db.execute(select(Account).filter(Account.id == account_id, Account.user_id == user_id))
    account = result.scalars().first()
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found or access denied"
        )
    return account

@router.post("/sub", status_code=status.HTTP_201_CREATED)
async def create_sub_account(
    request: SubAccountCreate,
    current_request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delegates sub-account creation to the account service.
    """
    name = request.name.strip()
    new_sub = await create_user_sub_account(
        db, current_user.id, name, current_request.client.host, 
        current_request.headers.get("user-agent")
    )
    
    return {"id": new_sub.id, "name": new_sub.name, "balance": int(new_sub.balance)}

@router.patch("/{account_id}")
async def rename_account(
    account_id: int,
    request: SubAccountRename,
    current_request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    name = request.name.strip()
    if not is_valid_name(name):
        raise HTTPException(status_code=400, detail="Name can only contain letters, numbers, and spaces")

    account = await check_account_owner(account_id, current_user.id, db)

    old_name = account.name
    account.name = name

    emit_activity(
        db, 
        current_user.id, 
        "sub_account", 
        "renamed", 
        f"Renamed sub-account '{old_name}' → '{name}'", 
        {
            "account_id": account.id,
            "old_name": old_name,
            "new_name": name,
        },
        ip=current_request.client.host,
        user_agent=current_request.headers.get("user-agent")
    )
    await db.commit()
    return {"id": account.id, "name": account.name}


@router.post("/transfer/internal")
async def internal_transfer(
    request: InternalTransferRequest,
    current_request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    sender, receiver = await execute_internal_transfer(
        db=db,
        user_id=current_user.id,
        from_account_id=request.from_account_id,
        to_account_id=request.to_account_id,
        amount=request.amount,
        commentary=request.commentary,
        client_ip=current_request.client.host,
        user_agent=current_request.headers.get("user-agent"),
        user_email=current_user.email
    )
    
    return {
        "status": "success", 
        "message": "Internal transfer completed",
        "sender_balance": int(sender.balance),
        "receiver_balance": int(receiver.balance)
    }



@router.get("/{account_id}/credentials")
async def get_account_credentials(
    account_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Securely retrieve unmasked account credentials."""
    account = await check_account_owner(account_id, current_user.id, db)

    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    if not account.account_number_encrypted:
        raise HTTPException(status_code=400, detail="Credentials not assigned to this account")

    full_account_number = decrypt_account_number(account.account_number_encrypted)
    
    return {
        "routing_number": account.routing_number,
        "account_number": full_account_number,
        "internal_reference_id": account.internal_reference_id,
        "masked_account_number": mask_account_number(full_account_number)
    }

@router.get("/{user_id}")
async def get_account_balance(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.id != user_id and current_user.role not in ["admin", "support"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="You do not have permission to access these accounts"
        )
    
    result = await db.execute(select(Account).filter(Account.user_id == user_id))
    accounts = result.scalars().all()
    if not accounts:
        raise HTTPException(status_code=404, detail="Account not found")

    total_balance_cents = sum(acc.balance for acc in accounts)
    total_reserved_cents = sum(acc.reserved_balance or 0 for acc in accounts)
    
    sub_accounts = [{
        "id": acc.id,
        "name": acc.name,
        "balance": int(acc.balance),
        "reserved_balance": int(acc.reserved_balance or 0),
        "is_main": acc.is_main,
        "routing_number": acc.routing_number,
        "masked_account_number": mask_account_number(decrypt_account_number(acc.account_number_encrypted)) if acc.account_number_encrypted else None
    } for acc in accounts]

    return {
        "balance": int(total_balance_cents), 
        "reserved_balance": int(total_reserved_cents),
        "user_id": user_id,
        "accounts": sub_accounts
    }
