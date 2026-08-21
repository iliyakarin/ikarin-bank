import random
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models import Institution, MasterAccount, FedwireTransfer
from schemas import FedwireOriginateRequest, FedwireTransferResponse
from routing_utils import validate_routing_number

router = APIRouter(prefix="/fed/wire", tags=["Fedwire Funds Service (RTGS)"])

def generate_imad(sender_district_id: int) -> str:
    now_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    letters = "ABCDEFGHIJKL"
    district_letter = letters[sender_district_id - 1] if 1 <= sender_district_id <= 12 else "L"
    seq = f"{random.randint(100000, 999999)}{random.randint(1000, 9999)}"
    return f"{now_str}{district_letter}1Q{seq}"

def generate_omad(receiver_district_id: int) -> str:
    now_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    letters = "ABCDEFGHIJKL"
    district_letter = letters[receiver_district_id - 1] if 1 <= receiver_district_id <= 12 else "B"
    seq = f"{random.randint(100000, 999999)}{random.randint(1000, 9999)}"
    return f"{now_str}{district_letter}1Q{seq}"

@router.post("/originate", response_model=FedwireTransferResponse)
async def originate_fedwire(payload: FedwireOriginateRequest, db: AsyncSession = Depends(get_db)):
    val_s = validate_routing_number(payload.sender_routing)
    val_r = validate_routing_number(payload.receiver_routing)
    if not val_s["valid"]:
        raise HTTPException(status_code=400, detail=f"Invalid sender routing number: {val_s['errors']}")
    if not val_r["valid"]:
        raise HTTPException(status_code=400, detail=f"Invalid receiver routing number: {val_r['errors']}")

    res = await db.execute(select(Institution).where(Institution.routing_number == payload.sender_routing))
    sender_inst = res.scalar_one_or_none()
    res = await db.execute(select(Institution).where(Institution.routing_number == payload.receiver_routing))
    receiver_inst = res.scalar_one_or_none()

    if not sender_inst:
        raise HTTPException(status_code=404, detail="Sender institution not found in Fed Directory")
    if not receiver_inst:
        raise HTTPException(status_code=404, detail="Receiver institution not found in Fed Directory")

    res = await db.execute(select(MasterAccount).where(MasterAccount.routing_number == payload.sender_routing))
    sender_ma = res.scalar_one_or_none()
    res = await db.execute(select(MasterAccount).where(MasterAccount.routing_number == payload.receiver_routing))
    receiver_ma = res.scalar_one_or_none()

    if sender_ma:
        available_liquidity = sender_ma.balance_cents + sender_ma.daylight_overdraft_limit_cents
        if payload.amount_cents > available_liquidity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error_code": "EXCEEDS_DAYLIGHT_OVERDRAFT", "message": "Transfer amount exceeds available master account reserve and daylight overdraft headroom"},
            )

    imad = generate_imad(sender_inst.district_id)
    omad = generate_omad(receiver_inst.district_id)
    wire = FedwireTransfer(
        imad=imad,
        omad=omad,
        business_function_code=payload.business_function_code,
        sender_routing=payload.sender_routing,
        sender_name=payload.sender_name,
        sender_account=payload.sender_account,
        receiver_routing=payload.receiver_routing,
        receiver_name=payload.receiver_name,
        receiver_account=payload.receiver_account,
        amount_cents=payload.amount_cents,
        charge_details=payload.charge_details,
        payment_reference=payload.payment_reference,
        status="SETTLED",
    )
    db.add(wire)

    if sender_ma:
        sender_ma.balance_cents -= payload.amount_cents
    if receiver_ma:
        receiver_ma.balance_cents += payload.amount_cents

    await db.commit()
    await db.refresh(wire)

    return FedwireTransferResponse(
        imad=wire.imad,
        omad=wire.omad,
        business_function_code=wire.business_function_code,
        sender_routing=wire.sender_routing,
        receiver_routing=wire.receiver_routing,
        amount_cents=wire.amount_cents,
        status=wire.status,
        settlement_timestamp=wire.settlement_timestamp,
    )

@router.get("/transfers/{imad}", response_model=FedwireTransferResponse)
async def get_fedwire_transfer(imad: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(FedwireTransfer).where(FedwireTransfer.imad == imad))
    wire = res.scalar_one_or_none()
    if not wire:
        raise HTTPException(status_code=404, detail="Fedwire transfer not found")
    return FedwireTransferResponse.model_validate(wire, from_attributes=True)
