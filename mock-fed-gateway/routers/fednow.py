import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models import Institution, MasterAccount, FedNowTransfer
from schemas import FedNowTransferRequest, FedNowRFPRequest, FedNowTransferResponse
from routing_utils import validate_routing_number

router = APIRouter(prefix="/fed/fednow", tags=["FedNow Instant Payments (24/7/365)"])

@router.post("/transfer", response_model=FedNowTransferResponse)
async def transfer_fednow(payload: FedNowTransferRequest, db: AsyncSession = Depends(get_db)):
    val_d = validate_routing_number(payload.debtor_routing)
    val_c = validate_routing_number(payload.creditor_routing)
    if not val_d["valid"] or not val_c["valid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"status": "RJCT", "status_reason_code": "AGNT", "description": "Incorrect routing identification"},
        )

    res = await db.execute(select(Institution).where(Institution.routing_number == payload.creditor_routing))
    cred_inst = res.scalar_one_or_none()
    if not cred_inst or not cred_inst.fednow_participant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"status": "RJCT", "status_reason_code": "AGNT", "description": "Creditor financial institution is not a FedNow participant"},
        )

    if "0000" in payload.creditor_account:
        end_to_end = payload.end_to_end_id or f"FEDNOW-{uuid.uuid4()}"
        instr_id = payload.instruction_id or f"INSTR-{uuid.uuid4()}"
        tx = FedNowTransfer(
            end_to_end_id=end_to_end,
            instruction_id=instr_id,
            message_type="CREDIT_TRANSFER",
            debtor_routing=payload.debtor_routing,
            debtor_name=payload.debtor_name,
            debtor_account=payload.debtor_account,
            creditor_routing=payload.creditor_routing,
            creditor_name=payload.creditor_name,
            creditor_account=payload.creditor_account,
            amount_cents=payload.amount_cents,
            status="RJCT",
            status_reason_code="AC04",
            status_reason_description="Closed Account Number",
        )
        db.add(tx)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"status": "RJCT", "status_reason_code": "AC04", "description": "Closed Account Number"},
        )

    end_to_end = payload.end_to_end_id or f"FEDNOW-{uuid.uuid4()}"
    instr_id = payload.instruction_id or f"INSTR-{uuid.uuid4()}"
    tx = FedNowTransfer(
        end_to_end_id=end_to_end,
        instruction_id=instr_id,
        message_type="CREDIT_TRANSFER",
        debtor_routing=payload.debtor_routing,
        debtor_name=payload.debtor_name,
        debtor_account=payload.debtor_account,
        creditor_routing=payload.creditor_routing,
        creditor_name=payload.creditor_name,
        creditor_account=payload.creditor_account,
        amount_cents=payload.amount_cents,
        status="ACCP",
    )
    db.add(tx)

    res = await db.execute(select(MasterAccount).where(MasterAccount.routing_number == payload.debtor_routing))
    debtor_ma = res.scalar_one_or_none()
    res = await db.execute(select(MasterAccount).where(MasterAccount.routing_number == payload.creditor_routing))
    cred_ma = res.scalar_one_or_none()

    if debtor_ma:
        debtor_ma.balance_cents -= payload.amount_cents
    if cred_ma:
        cred_ma.balance_cents += payload.amount_cents

    await db.commit()
    await db.refresh(tx)

    return FedNowTransferResponse(
        end_to_end_id=tx.end_to_end_id,
        instruction_id=tx.instruction_id,
        status="ACCP",
        amount_cents=tx.amount_cents,
        settlement_timestamp=tx.created_at,
    )

@router.post("/rfp")
async def request_for_payment(payload: FedNowRFPRequest, db: AsyncSession = Depends(get_db)):
    rfp_id = payload.rfp_id or f"RFP-{uuid.uuid4()}"
    tx = FedNowTransfer(
        end_to_end_id=rfp_id,
        instruction_id=f"INSTR-{uuid.uuid4()}",
        message_type="REQUEST_FOR_PAYMENT",
        debtor_routing=payload.debtor_routing,
        debtor_name=payload.debtor_name,
        debtor_account="",
        creditor_routing=payload.creditor_routing,
        creditor_name=payload.creditor_name,
        creditor_account="",
        amount_cents=payload.amount_cents,
        status="PEND",
    )
    db.add(tx)
    await db.commit()
    return {"rfp_id": rfp_id, "status": "PRESENTED_TO_DEBTOR", "amount_cents": payload.amount_cents}

@router.get("/transfers/{end_to_end_id}", response_model=FedNowTransferResponse)
async def get_fednow_transfer(end_to_end_id: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(FedNowTransfer).where(FedNowTransfer.end_to_end_id == end_to_end_id))
    tx = res.scalar_one_or_none()
    if not tx:
        raise HTTPException(status_code=404, detail="FedNow transfer not found")
    return FedNowTransferResponse(
        end_to_end_id=tx.end_to_end_id,
        instruction_id=tx.instruction_id,
        status=tx.status,
        status_reason_code=tx.status_reason_code,
        status_reason_description=tx.status_reason_description,
        amount_cents=tx.amount_cents,
        settlement_timestamp=tx.created_at,
    )
