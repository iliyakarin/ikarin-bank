from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from database import get_db
from models import MasterAccount, ACHTransaction, FedwireTransfer, FedNowTransfer
from schemas import (
    MasterAccountResponse,
    MasterAccountAdjustRequest,
    DailyStatementResponse,
)

router = APIRouter(prefix="/fed", tags=["Fed Master Account & Settlement"])

@router.get("/master-account/{routing_number}", response_model=MasterAccountResponse)
async def get_master_account(routing_number: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(MasterAccount).where(MasterAccount.routing_number == routing_number))
    ma = res.scalar_one_or_none()
    if not ma:
        raise HTTPException(status_code=404, detail="Master account not found for institution")
    
    avail = ma.balance_cents + ma.daylight_overdraft_limit_cents
    return MasterAccountResponse(
        account_number=ma.account_number,
        routing_number=ma.routing_number,
        currency=ma.currency,
        balance_cents=ma.balance_cents,
        daylight_overdraft_limit_cents=ma.daylight_overdraft_limit_cents,
        available_liquidity_cents=avail,
        status=ma.status,
        updated_at=ma.updated_at,
    )

@router.post("/master-account/adjust", response_model=MasterAccountResponse)
async def adjust_master_account(payload: MasterAccountAdjustRequest, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(MasterAccount).where(MasterAccount.routing_number == payload.routing_number))
    ma = res.scalar_one_or_none()
    if not ma:
        raise HTTPException(status_code=404, detail="Master account not found for institution")
    
    ma.balance_cents += payload.adjustment_cents
    await db.commit()
    await db.refresh(ma)

    avail = ma.balance_cents + ma.daylight_overdraft_limit_cents
    return MasterAccountResponse(
        account_number=ma.account_number,
        routing_number=ma.routing_number,
        currency=ma.currency,
        balance_cents=ma.balance_cents,
        daylight_overdraft_limit_cents=ma.daylight_overdraft_limit_cents,
        available_liquidity_cents=avail,
        status=ma.status,
        updated_at=ma.updated_at,
    )

@router.get("/statements/{routing_number}", response_model=DailyStatementResponse)
async def get_daily_statement(routing_number: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(MasterAccount).where(MasterAccount.routing_number == routing_number))
    ma = res.scalar_one_or_none()
    if not ma:
        raise HTTPException(status_code=404, detail="Master account not found")

    today = datetime.now(timezone.utc).date()

    ach_deb = (await db.execute(
        select(func.coalesce(func.sum(ACHTransaction.amount_cents), 0)).where(
            ACHTransaction.originator_routing == routing_number,
            ACHTransaction.entry_class == "DEBIT",
            ACHTransaction.status == "SETTLED",
        )
    )).scalar_one()

    ach_cred = (await db.execute(
        select(func.coalesce(func.sum(ACHTransaction.amount_cents), 0)).where(
            ACHTransaction.receiver_routing == routing_number,
            ACHTransaction.entry_class == "CREDIT",
            ACHTransaction.status == "SETTLED",
        )
    )).scalar_one()

    wire_deb = (await db.execute(
        select(func.coalesce(func.sum(FedwireTransfer.amount_cents), 0)).where(
            FedwireTransfer.sender_routing == routing_number,
            FedwireTransfer.status == "SETTLED",
        )
    )).scalar_one()

    wire_cred = (await db.execute(
        select(func.coalesce(func.sum(FedwireTransfer.amount_cents), 0)).where(
            FedwireTransfer.receiver_routing == routing_number,
            FedwireTransfer.status == "SETTLED",
        )
    )).scalar_one()

    now_deb = (await db.execute(
        select(func.coalesce(func.sum(FedNowTransfer.amount_cents), 0)).where(
            FedNowTransfer.debtor_routing == routing_number,
            FedNowTransfer.status == "ACCP",
        )
    )).scalar_one()

    now_cred = (await db.execute(
        select(func.coalesce(func.sum(FedNowTransfer.amount_cents), 0)).where(
            FedNowTransfer.creditor_routing == routing_number,
            FedNowTransfer.status == "ACCP",
        )
    )).scalar_one()

    total_count = (await db.execute(
        select(func.count()).select_from(ACHTransaction).where(ACHTransaction.originator_routing == routing_number)
    )).scalar_one()

    opening = ma.balance_cents + int(wire_deb) + int(now_deb) - int(wire_cred) - int(now_cred)

    return DailyStatementResponse(
        routing_number=routing_number,
        statement_date=today,
        opening_balance_cents=opening,
        closing_balance_cents=ma.balance_cents,
        ach_debits_cents=int(ach_deb),
        ach_credits_cents=int(ach_cred),
        fedwire_debits_cents=int(wire_deb),
        fedwire_credits_cents=int(wire_cred),
        fednow_debits_cents=int(now_deb),
        fednow_credits_cents=int(now_cred),
        total_transactions_count=total_count,
    )
