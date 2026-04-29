"""Account Management Router.

This module provides endpoints for managing user accounts, including sub-account
creation, renaming, internal transfers, and credential retrieval.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import re

from database import SessionLocal
from models.user import User
from models.account import Account
from models.transaction import Transaction
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
from schemas.accounts import (
    SubAccountCreate, SubAccountRename, InternalTransferRequest,
    AccountResponse, BalanceResponse, AccountCredentialsResponse
)

router = APIRouter(prefix="/accounts", tags=["accounts"])

def is_valid_name(name: str) -> bool:
    """Minimal validation for account names."""
    return bool(re.match(r"^[a-zA-Z0-9 ]+$", name))

async def check_account_owner(account_id: int, user_id: int, db: AsyncSession) -> Account:
    """Ensures an account exists and belongs to the specified user."""
    result = await db.execute(select(Account).where(Account.id == account_id, Account.user_id == user_id))
    account = result.scalars().first()
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found or access denied"
        )
    return account

@router.get("", response_model=BalanceResponse)
async def get_my_accounts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns all accounts for the currently authenticated user."""
    accounts = (await db.execute(select(Account).where(Account.user_id == current_user.id))).scalars().all()
    if not accounts:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No accounts found")

    sub_accounts_data = []
    for acc in accounts:
        masked = mask_account_number(decrypt_account_number(acc.account_number_encrypted)) if acc.account_number_encrypted else None
        sub_accounts_data.append(AccountResponse(
            id=acc.id, name=acc.name, balance=acc.balance, reserved_balance=acc.reserved_balance or 0,
            is_main=acc.is_main, routing_number=acc.routing_number, masked_account_number=masked
        ))

    return BalanceResponse(
        balance=sum(acc.balance for acc in accounts),
        reserved_balance=sum(acc.reserved_balance or 0 for acc in accounts),
        user_id=current_user.id, accounts=sub_accounts_data
    )

@router.post("/sub", status_code=status.HTTP_201_CREATED, response_model=AccountResponse)
async def create_sub_account(
    request: SubAccountCreate,
    current_request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Creates a new sub-account for the authenticated user.

    Validates the account name and delegates creation to the account service.

    Args:
        request (SubAccountCreate): The data for the new sub-account.
        current_request (Request): The incoming request.
        current_user (User): The authenticated user.
        db (AsyncSession): The database session.

    Returns:
        AccountResponse: The newly created sub-account details.

    Raises:
        HTTPException: If the name is invalid.
    """
    name = request.name.strip()
    if not is_valid_name(name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Name can only contain letters, numbers, and spaces"
        )
    
    new_sub = await create_user_sub_account(
        db, current_user.id, name, current_request.client.host,
        current_request.headers.get("user-agent")
    )
    return new_sub

@router.patch("/{account_id}", response_model=AccountResponse)
async def rename_account(
    account_id: int,
    request: SubAccountRename,
    current_request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    name = request.name.strip()
    if not is_valid_name(name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Name can only contain letters, numbers, and spaces"
        )

    account = await check_account_owner(account_id, current_user.id, db)
    old_name = account.name
    account.name = name

    emit_activity(
        db, current_user.id, "sub_account", "renamed", f"Renamed '{old_name}' to '{name}'",
        {"account_id": account.id, "old_name": old_name, "new_name": name},
        ip=current_request.client.host, user_agent=current_request.headers.get("user-agent")
    )
    await db.commit()
    await db.refresh(account)
    return account

@router.post("/transfer/internal")
async def internal_transfer(
    request: InternalTransferRequest,
    current_request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Executes a transfer between two accounts owned by the same user.

    Args:
        request (InternalTransferRequest): The transfer details (amount, accounts).
        current_request (Request): The incoming request.
        current_user (User): The authenticated user.
        db (AsyncSession): The database session.

    Returns:
        dict: A success message and updated account balances.
    """
    sender, receiver = await execute_internal_transfer(
        db=db, user_id=current_user.id, from_id=request.from_account_id, to_id=request.to_account_id,
        amount=request.amount, comm=request.commentary, ip=current_request.client.host,
        ua=current_request.headers.get("user-agent"), email=current_user.email
    )
    return {
        "status": "success", "message": "Internal transfer completed",
        "sender_balance": int(sender.balance), "receiver_balance": int(receiver.balance)
    }

@router.get("/{account_id}/credentials", response_model=AccountCredentialsResponse)
async def get_account_credentials(
    account_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    account = await check_account_owner(account_id, current_user.id, db)
    if not account.account_number_encrypted:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No credentials")
    full = decrypt_account_number(account.account_number_encrypted)
    return {
        "routing_number": account.routing_number, "account_number": full,
        "internal_reference_id": account.internal_reference_id, "masked_account_number": mask_account_number(full)
    }

@router.get("/{user_id}", response_model=BalanceResponse)
async def get_account_balance(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.id != user_id and current_user.role not in ["admin", "support"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    accounts = (await db.execute(select(Account).where(Account.user_id == user_id))).scalars().all()
    if not accounts: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    sub_accounts_data = []
    for acc in accounts:
        masked = mask_account_number(decrypt_account_number(acc.account_number_encrypted)) if acc.account_number_encrypted else None
        sub_accounts_data.append(AccountResponse(
            id=acc.id, name=acc.name, balance=acc.balance, reserved_balance=acc.reserved_balance or 0,
            is_main=acc.is_main, routing_number=acc.routing_number, masked_account_number=masked
        ))

    return BalanceResponse(
        balance=sum(acc.balance for acc in accounts),
        reserved_balance=sum(acc.reserved_balance or 0 for acc in accounts),
        user_id=user_id, accounts=sub_accounts_data
    )
