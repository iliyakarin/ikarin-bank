import uuid
import random
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models import Institution, MasterAccount, ACHTransaction
from schemas import (
    ACHOriginateRequest,
    ACHBatchRequest,
    ACHTransactionResponse,
    ACHBatchResponse,
)
from routing_utils import validate_routing_number

router = APIRouter(prefix="/fed/ach", tags=["FedACH Services"])

RETURN_REASONS = {
    "R01": "Insufficient Funds",
    "R02": "Account Closed",
    "R03": "No Account / Unable to Locate Account",
    "R04": "Invalid Account Number Structure / Routing",
    "R06": "Returned per ODFI Request",
    "R07": "Notice of Change / Authorization Revoked",
    "R08": "Payment Stopped",
    "R10": "Customer Advises Not Authorized",
    "R16": "Account Frozen",
    "R20": "Non-Transaction Account",
}

def determine_ach_return_code(
    amount_cents: int,
    receiver_account: str,
    override_header: str | None = None,
) -> str | None:
    if override_header and override_header in RETURN_REASONS:
        return override_header
    if "00000" in receiver_account:
        return "R03"
    cents_rem = amount_cents % 100
    if cents_rem == 1:
        return "R01"
    if cents_rem == 2:
        return "R02"
    if cents_rem == 8:
        return "R08"
    if cents_rem == 10:
        return "R10"
    if cents_rem == 16:
        return "R16"
    if cents_rem == 20:
        return "R20"
    return None

@router.post("/originate", response_model=ACHTransactionResponse)
async def originate_ach(
    payload: ACHOriginateRequest,
    x_fed_simulate_return: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
):
    orig_rtn = payload.originator_routing or "123456780"
    recv_rtn = payload.receiver_routing or payload.routing_number
    recv_acct = payload.receiver_account or payload.account_number or "100001"

    if not recv_rtn:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": "R04", "message": "Missing receiver routing number"},
        )

    # 1. Validate RTN against Directory
    val = validate_routing_number(recv_rtn)
    if not val["valid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": "R04", "message": f"Invalid routing number: {val['errors']}"},
        )

    res = await db.execute(select(Institution).where(Institution.routing_number == recv_rtn))
    inst = res.scalar_one_or_none()
    if not inst:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "R04", "message": "Receiver institution not found in Fed Directory"},
        )

    amount_cents = int(round(payload.amount * 100)) if isinstance(payload.amount, float) else int(payload.amount)

    # 2. Check Failure Triggers
    return_code = determine_ach_return_code(amount_cents, recv_acct, x_fed_simulate_return)
    if return_code:
        reason = RETURN_REASONS.get(return_code, "ACH Return")
        tx_id = str(uuid.uuid4())
        trace_num = f"{recv_rtn[:8]}{random.randint(1000000, 9999999)}"
        ach_entry = ACHTransaction(
            id=tx_id,
            sec_code=payload.sec_code,
            originator_routing=orig_rtn,
            originator_name=payload.originator_name or "Originator",
            originator_account=payload.originator_account or "100001",
            receiver_routing=recv_rtn,
            receiver_name=payload.receiver_name or inst.name,
            receiver_account=recv_acct,
            amount_cents=amount_cents,
            entry_class=payload.entry_class,
            payment_description=payload.payment_description or "ACH Transfer",
            status="RETURNED",
            return_code=return_code,
            return_reason=reason,
            trace_number=trace_num,
        )
        db.add(ach_entry)
        await db.commit()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": return_code, "message": reason, "trace_number": trace_num},
        )

    # 3. Successful ACH settlement
    tx_id = str(uuid.uuid4())
    trace_num = f"{recv_rtn[:8]}{random.randint(1000000, 9999999)}"
    ach_entry = ACHTransaction(
        id=tx_id,
        sec_code=payload.sec_code,
        originator_routing=orig_rtn,
        originator_name=payload.originator_name or "Originator",
        originator_account=payload.originator_account or "100001",
        receiver_routing=recv_rtn,
        receiver_name=payload.receiver_name or inst.name,
        receiver_account=recv_acct,
        amount_cents=amount_cents,
        entry_class=payload.entry_class,
        payment_description=payload.payment_description or "ACH Transfer",
        status="SETTLED",
        trace_number=trace_num,
    )
    db.add(ach_entry)

    res = await db.execute(select(MasterAccount).where(MasterAccount.routing_number == orig_rtn))
    orig_ma = res.scalar_one_or_none()
    res = await db.execute(select(MasterAccount).where(MasterAccount.routing_number == recv_rtn))
    recv_ma = res.scalar_one_or_none()
    if orig_ma and recv_ma:
        if payload.entry_class == "DEBIT":
            orig_ma.balance_cents += amount_cents
            recv_ma.balance_cents -= amount_cents
        else:
            orig_ma.balance_cents -= amount_cents
            recv_ma.balance_cents += amount_cents

    await db.commit()
    await db.refresh(ach_entry)

    return ACHTransactionResponse(
        id=ach_entry.id,
        trace_number=ach_entry.trace_number,
        sec_code=ach_entry.sec_code,
        originator_routing=ach_entry.originator_routing,
        receiver_routing=ach_entry.receiver_routing,
        amount_cents=ach_entry.amount_cents,
        entry_class=ach_entry.entry_class,
        status="SETTLED",
        settlement_date=ach_entry.settlement_date,
        message=f"ACH Origination Settled with {inst.name}",
    )

@router.post("/batches", response_model=ACHBatchResponse)
async def originate_ach_batch(batch: ACHBatchRequest, db: AsyncSession = Depends(get_db)):
    batch_id = f"BATCH-{uuid.uuid4()}"
    settled = 0
    returned = 0
    total_debits = 0
    total_credits = 0
    tx_responses = []

    for entry in batch.entries:
        amt_cents = int(round(entry.amount * 100)) if isinstance(entry.amount, float) else int(entry.amount)
        if entry.entry_class == "DEBIT":
            total_debits += amt_cents
        else:
            total_credits += amt_cents

        return_code = determine_ach_return_code(amt_cents, entry.receiver_account)
        status_val = "RETURNED" if return_code else "SETTLED"
        reason = RETURN_REASONS.get(return_code) if return_code else None

        if status_val == "SETTLED":
            settled += 1
        else:
            returned += 1

        tx_id = str(uuid.uuid4())
        trace_num = f"{entry.receiver_routing[:8]}{random.randint(1000000, 9999999)}"
        ach_entry = ACHTransaction(
            id=tx_id,
            batch_id=batch_id,
            sec_code=entry.sec_code,
            originator_routing=batch.originator_routing,
            originator_name=batch.originator_name,
            originator_account=batch.originator_account,
            receiver_routing=entry.receiver_routing,
            receiver_name=entry.receiver_name,
            receiver_account=entry.receiver_account,
            amount_cents=amt_cents,
            entry_class=entry.entry_class,
            payment_description=entry.payment_description or "Batch ACH",
            status=status_val,
            return_code=return_code,
            return_reason=reason,
            trace_number=trace_num,
        )
        db.add(ach_entry)
        tx_responses.append(ACHTransactionResponse(
            id=tx_id,
            trace_number=trace_num,
            sec_code=entry.sec_code,
            originator_routing=batch.originator_routing,
            receiver_routing=entry.receiver_routing,
            amount_cents=amt_cents,
            entry_class=entry.entry_class,
            status=status_val,
            return_code=return_code,
            return_reason=reason,
            settlement_date=datetime.now(timezone.utc).date(),
        ))

    await db.commit()
    return ACHBatchResponse(
        batch_id=batch_id,
        total_entries=len(batch.entries),
        settled_count=settled,
        returned_count=returned,
        total_debits_cents=total_debits,
        total_credits_cents=total_credits,
        transactions=tx_responses,
    )

@router.get("/transactions/{id}", response_model=ACHTransactionResponse)
async def get_ach_transaction(id: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(ACHTransaction).where(ACHTransaction.id == id))
    tx = res.scalar_one_or_none()
    if not tx:
        raise HTTPException(status_code=404, detail="ACH transaction not found")
    return ACHTransactionResponse.model_validate(tx, from_attributes=True)
