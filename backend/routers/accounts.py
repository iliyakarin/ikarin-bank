import re
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from pydantic import BaseModel
from typing import Optional, List
from database import Account, User, Transaction, SessionLocal
from activity import emit_activity
from account_service import assign_account_credentials, decrypt_account_number, mask_account_number
import datetime
import uuid

# Assume these dependencies are imported from main or structured accordingly
from auth_utils import get_db, get_current_user

router = APIRouter(
    prefix="/v1/accounts",
    tags=["Accounts"],
)

class SubAccountCreate(BaseModel):
    name: str

class SubAccountRename(BaseModel):
    name: str

class InternalTransferRequest(BaseModel):
    from_account_id: int
    to_account_id: int
    amount: Decimal
    commentary: Optional[str] = None

def is_valid_name(name: str) -> bool:
    """Validate name contains only letters, numbers, and spaces."""
    if not name:
        return False
    return bool(re.match(r"^[a-zA-Z0-9 ]+$", name))

async def check_account_owner(account_id: int, user_id: int, db: AsyncSession):
    """Verify that the account exists and belongs to the specified user."""
    result = await db.execute(select(Account).filter(Account.id == account_id, Account.user_id == user_id))
    account = result.scalars().first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found or access denied")
    return account

@router.post("/sub", status_code=status.HTTP_201_CREATED)
async def create_sub_account(
    request: SubAccountCreate,
    current_request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    name = request.name.strip()
    if not is_valid_name(name):
        raise HTTPException(status_code=400, detail="Name can only contain letters, numbers, and spaces")

    # Check constraint: max 10 sub-accounts
    result = await db.execute(select(func.count(Account.id)).filter(
        Account.user_id == current_user.id,
        Account.is_main == False
    ))
    sub_account_count = result.scalar()

    if sub_account_count >= 10:
        raise HTTPException(status_code=400, detail="Maximum of 10 sub-accounts reached")

    # Find the main account to link as parent (assuming at least one exists)
    result = await db.execute(select(Account).filter(
        Account.user_id == current_user.id,
        Account.is_main == True
    ))
    main_account = result.scalars().first()

    if not main_account:
        raise HTTPException(status_code=404, detail="Main account not found")

    new_sub = Account(
        user_id=current_user.id,
        is_main=False,
        parent_account_id=main_account.id,
        name=name,
        balance=Decimal("0.00"),
        reserved_balance=Decimal("0.00")
    )
    await assign_account_credentials(db, new_sub)
    db.add(new_sub)

    emit_activity(
        db, 
        current_user.id, 
        "sub_account", 
        "created", 
        f"Created sub-account '{name}'", 
        {
            "account_id": None,  # Will be set after commit
            "name": name,
            "sub_count": sub_account_count + 1,
        },
        ip=current_request.client.host,
        user_agent=current_request.headers.get("user-agent")
    )
    await db.commit()
    await db.refresh(new_sub)
    
    return {"id": new_sub.id, "name": new_sub.name, "balance": float(new_sub.balance)}

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
    if request.amount <= 0:
         raise HTTPException(status_code=400, detail="Transfer amount must be positive")

    if request.from_account_id == request.to_account_id:
        raise HTTPException(status_code=400, detail="Cannot transfer to the same account")

    # Determine lock order to prevent deadlocks (lowest ID first)
    first_id, second_id = sorted([request.from_account_id, request.to_account_id])

    # Enforce atomic transaction and lock rows
    try:
        res1 = await db.execute(select(Account).filter(Account.id == first_id, Account.user_id == current_user.id).with_for_update())
        acc1 = res1.scalars().first()
        res2 = await db.execute(select(Account).filter(Account.id == second_id, Account.user_id == current_user.id).with_for_update())
        acc2 = res2.scalars().first()

        if not acc1 or not acc2:
             raise HTTPException(status_code=404, detail="One or more accounts not found or access denied")

        if first_id == request.from_account_id:
             sender = acc1
             receiver = acc2
        else:
             sender = acc2
             receiver = acc1

        # Check funds AFTER locks are acquired to ensure no simultaneous deductions cause an overdraft
        if sender.balance < request.amount:
             raise HTTPException(status_code=400, detail="Insufficient funds in source account")

        # Deduct from sender first, then credit receiver
        sender.balance -= request.amount
        receiver.balance += request.amount

        # Record Transactions
        tx_id_parent = str(uuid.uuid4())
        
        sender_tx = Transaction(
            id=str(uuid.uuid4()),
            parent_id=tx_id_parent,
            account_id=sender.id,
            amount=-request.amount,
            category="Internal Transfer",
            merchant=f"Transfer to {receiver.name}",
            status="cleared", # internal transfers clear instantly
            transaction_type="transfer",
            transaction_side="DEBIT",
            commentary=request.commentary
        )
        
        receiver_tx = Transaction(
            id=str(uuid.uuid4()),
            parent_id=tx_id_parent,
            account_id=receiver.id,
            amount=request.amount,
            category="Internal Transfer",
            merchant=f"Transfer from {sender.name}",
            status="cleared",
            transaction_type="transfer",
            transaction_side="CREDIT",
            commentary=request.commentary
        )

        db.add(sender_tx)
        db.add(receiver_tx)

        emit_activity(
            db, 
            current_user.id, 
            "sub_account", 
            "transfer", 
            f"Transferred ${float(request.amount):.2f} from {sender.name} to {receiver.name}", 
            {
                "from_account": sender.name,
                "to_account": receiver.name,
                "amount": float(request.amount),
                "transaction_id": tx_id_parent,
            },
            ip=current_request.client.host,
            user_agent=current_request.headers.get("user-agent")
        )
        
        await db.commit()
        
        return {
            "status": "success", 
            "message": "Internal transfer completed",
            "sender_balance": float(sender.balance),
            "receiver_balance": float(receiver.balance)
        }
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Internal transfer failed")


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

