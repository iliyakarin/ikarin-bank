"""Financial Transfers Router.

This module handles P2P transfers, payment requests, and scheduled payments.
It orchestrates complex business logic by delegating to the transfer service.
"""
import datetime
import uuid
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.exc import SQLAlchemyError

from database import SessionLocal
from models.user import User
from models.account import Account
from models.transaction import Transaction, PaymentRequest, IdempotencyKey
from models.management import Outbox, ScheduledPayment
from schemas.transfers import (
    TransferRequest, P2PTransferRequest, PaymentRequestCreate, 
    PaymentRequestCounter, ScheduledTransferCreate, ScheduledPaymentResponse,
    WireTransferRequest, FedNowTransferRequest, ExternalACHTransferRequest
)
from auth_utils import get_db, get_current_user
from services.account_service import get_owned_account
from services.transfer_service import process_p2p_transfer, get_vendors
from services.event_emitter import emit_transactional_event
from activity import emit_activity, emit_transaction_status_update
from money_utils import from_cents
from idempotency import check_idempotency, complete_idempotency
from config import settings
import httpx

FED_GATEWAY_URL = getattr(settings, "MOCK_FED_GATEWAY_URL", "http://mock-fed-gateway:8002")

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Transfers"])

@router.post("/transfer")
async def create_transfer(
    transfer: TransferRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Executes a legacy single-account transfer (expense).

    Args:
        transfer (TransferRequest): The transfer details.
        request (Request): The incoming request.
        db (AsyncSession): The database session.
        current_user (User): The authenticated user.

    Returns:
        dict: Success status and transaction ID.
    """
    if transfer.idempotency_key:
        saved = await check_idempotency(db, transfer.idempotency_key, current_user.id)
        if saved is not None:
            return saved

    account = (await db.execute(
        select(Account).where(Account.id == transfer.account_id, Account.user_id == current_user.id)
    )).scalars().first()

    if not account:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account not found or access denied")

    client_ip = request.client.host if request.client else "0.0.0.0"
    user_agent = request.headers.get("user-agent", "unknown")

    tx_id = await emit_transactional_event(
        db=db,
        user_id=current_user.id,
        account_id=transfer.account_id,
        amount=transfer.amount,
        category=transfer.category,
        merchant=transfer.merchant,
        transaction_type="expense",
        transaction_side="DEBIT",
        sender_email=current_user.email,
        recipient_email="external@gateway.com",
        internal_account_last_4=account.account_number_last_4,
        event_type="transaction.created",
        idempotency_key=transfer.idempotency_key or str(uuid.uuid4()),
        ip_address=client_ip,
        user_agent=user_agent,
        status="cleared",
        activity_category="transfer",
        activity_action="sent",
    )

    response_body = {"status": "success", "transaction_id": tx_id}
    if transfer.idempotency_key:
        await complete_idempotency(db, transfer.idempotency_key, response_body)

    await db.commit()
    return response_body

@router.post("/p2p-transfer")
async def create_p2p_transfer(
    transfer: P2PTransferRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Executes a Peer-to-Peer (P2P) transfer.

    Orchestrates the transfer process, including idempotency checks, balance
    validation, and transactional event emission.

    Args:
        transfer (P2PTransferRequest): The P2P transfer data.
        request (Request): The incoming request.
        db (AsyncSession): The database session.
        current_user (User): The authenticated user.

    Returns:
        dict: The response from the transfer service.

    Raises:
        Exception: Re-raises exceptions from the transfer service.
    """
    # Phase 1: idempotency check — returns saved response on replay, None to proceed
    if transfer.idempotency_key:
        saved = await check_idempotency(db, transfer.idempotency_key, current_user.id)
        if saved is not None:
            return saved

    try:
        response_body = await process_p2p_transfer(
            db=db, current_user=current_user, recipient_email=transfer.recipient_email,
            amount=transfer.amount, source_account_id=transfer.source_account_id,
            commentary=transfer.commentary, idempotency_key=transfer.idempotency_key,
            payment_request_id=transfer.payment_request_id,
            client_ip=request.client.host, user_agent=request.headers.get("user-agent", "unknown"),
            subscriber_id=transfer.subscriber_id
        )

        # Phase 2: store response so future replays return the original result
        if transfer.idempotency_key:
            await complete_idempotency(db, transfer.idempotency_key, response_body)

        await db.commit()
        return response_body

    except Exception as e:
        await db.rollback()
        raise e

@router.post("/requests/create")
async def create_payment_request(
    request_data: PaymentRequestCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if request_data.amount <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Amount must be > 0")
    if request_data.target_email == current_user.email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot request from yourself")

    target = (await db.execute(select(User).where(User.email == request_data.target_email))).scalars().first()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target user not found")

    new_request = PaymentRequest(
        requester_id=current_user.id, target_email=request_data.target_email,
        amount=request_data.amount, purpose=request_data.purpose, status="pending_target"
    )
    db.add(new_request)

    emit_activity(db, current_user.id, "p2p", "requested", f"Requested {from_cents(request_data.amount)} from {request_data.target_email}", {
        "target_email": request_data.target_email, "amount": request_data.amount, "purpose": request_data.purpose,
    })
    await db.commit()
    return {"status": "success", "request_id": new_request.id}

@router.get("/requests")
async def get_payment_requests(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve payment requests involving the current user."""
    stmt = select(PaymentRequest).where(
        or_(PaymentRequest.requester_id == current_user.id, PaymentRequest.target_email == current_user.email)
    ).order_by(PaymentRequest.updated_at.desc())
    requests = (await db.execute(stmt)).scalars().all()

    # Load requesters to avoid N+1
    requester_ids = {req.requester_id for req in requests}
    users_result = await db.execute(select(User).where(User.id.in_(requester_ids)))
    user_map = {u.id: u for u in users_result.scalars().all()}

    result = []
    for req in requests:
        requester = user_map.get(req.requester_id)
        is_self = requester and requester.id == current_user.id
        name = f"{requester.first_name} {requester.last_name}" if is_self else (f"{requester.first_name} {requester.last_name[0]}." if requester else "Unknown")
        
        result.append({
            "id": req.id, "requester_id": req.requester_id, "requester_name": name,
            "requester_email": requester.email if requester else "unknown",
            "target_email": req.target_email, "amount": req.amount, "purpose": req.purpose,
            "status": req.status, "created_at": req.created_at.isoformat(), "updated_at": req.updated_at.isoformat()
        })
    return result

@router.post("/requests/{request_id}/decline")
async def decline_payment_request(
    request_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    req = (await db.execute(select(PaymentRequest).where(PaymentRequest.id == request_id))).scalars().first()
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    if req.requester_id != current_user.id and req.target_email != current_user.email:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    req.status = "declined"
    req.updated_at = datetime.datetime.now(datetime.timezone.utc)
    
    emit_activity(db, current_user.id, "p2p", "request_declined", f"Declined request #{req.id}", {"amount": req.amount})
    await db.commit()
    return {"status": "success", "new_status": req.status}

@router.get("/scheduled", response_model=List[ScheduledPaymentResponse])
async def get_scheduled_payments(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return (await db.execute(
        select(ScheduledPayment).where(ScheduledPayment.user_id == current_user.id).order_by(ScheduledPayment.id.desc())
    )).scalars().all()


@router.post("/transfers/scheduled")
async def create_scheduled_payment(
    payload: ScheduledTransferCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Creates a new scheduled payment."""
    if payload.idempotency_key:
        saved = await check_idempotency(db, payload.idempotency_key, current_user.id)
        if saved is not None:
            return saved

    from date_utils import calculate_next_run_at
    import datetime
    now = datetime.datetime.now(datetime.timezone.utc)
    next_run = calculate_next_run_at(now, payload.frequency)

    new_payment = ScheduledPayment(
        user_id=current_user.id,
        recipient_email=payload.recipient_email,
        amount=payload.amount,
        frequency=payload.frequency,
        frequency_interval=payload.frequency_interval,
        start_date=payload.start_date,
        end_condition=payload.end_condition,
        end_date=payload.end_date,
        target_payments=payload.target_payments,
        reserve_amount=payload.reserve_amount,
        funding_account_id=payload.funding_account_id,
        subscriber_id=payload.subscriber_id,
        idempotency_key=payload.idempotency_key,
        status="Active",
        next_run_at=next_run,
        payments_made=0,
        retry_count=0,
    )
    db.add(new_payment)
    await db.commit()
    await db.refresh(new_payment)

    response_body = {"scheduled_payment_id": new_payment.id, "status": "created"}
    if payload.idempotency_key:
        await complete_idempotency(db, payload.idempotency_key, response_body)
        await db.commit()
    return response_body


@router.post("/transfers/scheduled/{payment_id}/cancel")
async def cancel_scheduled_payment(
    payment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cancels an active scheduled payment."""
    payment = (await db.execute(
        select(ScheduledPayment).where(
            ScheduledPayment.id == payment_id,
            ScheduledPayment.user_id == current_user.id
        )
    )).scalars().first()

    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scheduled payment not found")
    if payment.status in ("Completed", "Failed", "Cancelled"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Cannot cancel a payment with status '{payment.status}'")

    payment.status = "Cancelled"
    payment.next_run_at = None
    await db.commit()
    return {"status": "cancelled", "payment_id": payment_id}


@router.post("/transfers/wire")
async def create_wire_transfer(
    payload: WireTransferRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Executes an outgoing Fedwire Funds Service (RTGS) high-value transfer."""
    if payload.idempotency_key:
        saved = await check_idempotency(db, payload.idempotency_key, current_user.id)
        if saved is not None:
            return saved

    account = await get_owned_account(db, payload.account_id, current_user.id)
    if account.balance < payload.amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient funds for Fedwire transfer",
        )

    # Call Mock Fed Gateway Fedwire endpoint
    async with httpx.AsyncClient() as client:
        try:
            fed_res = await client.post(
                f"{FED_GATEWAY_URL}/fed/wire/originate",
                json={
                    "sender_routing": "123456780",
                    "sender_name": f"{current_user.first_name} {current_user.last_name}".strip() or current_user.email,
                    "sender_account": account.account_number_last_4,
                    "receiver_routing": payload.receiver_routing,
                    "receiver_name": payload.receiver_name,
                    "receiver_account": payload.receiver_account,
                    "amount_cents": payload.amount,
                    "business_function_code": payload.business_function_code,
                    "payment_reference": payload.payment_reference,
                },
                headers={"X-API-KEY": settings.GATEWAY_API_KEY},
                timeout=8.0,
            )
            if fed_res.status_code != 200:
                err = fed_res.json().get("detail", "Fedwire transfer rejected by Federal Reserve")
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err)
            wire_data = fed_res.json()
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Fedwire communication failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Federal Reserve Fedwire gateway unavailable",
            )

    client_ip = request.client.host if request.client else "0.0.0.0"
    user_agent = request.headers.get("user-agent", "unknown")

    tx_id = await emit_transactional_event(
        db=db,
        user_id=current_user.id,
        account_id=payload.account_id,
        amount=payload.amount,
        category="Wire Transfer",
        merchant=payload.receiver_name,
        transaction_type="wire",
        transaction_side="DEBIT",
        sender_email=current_user.email,
        recipient_email=f"wire@{payload.receiver_routing}.fed",
        internal_account_last_4=account.account_number_last_4,
        event_type="transaction.created",
        idempotency_key=payload.idempotency_key or str(uuid.uuid4()),
        ip_address=client_ip,
        user_agent=user_agent,
        status="cleared",
        activity_category="transfer",
        activity_action="sent",
    )

    response_body = {
        "status": "success",
        "imad": wire_data.get("imad"),
        "omad": wire_data.get("omad"),
        "settlement_timestamp": wire_data.get("settlement_timestamp"),
        "transaction_id": tx_id,
    }
    if payload.idempotency_key:
        await complete_idempotency(db, payload.idempotency_key, response_body)

    await db.commit()
    return response_body


@router.post("/transfers/fednow")
async def create_fednow_transfer(
    payload: FedNowTransferRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Executes a 24/7/365 FedNow instant credit transfer."""
    if payload.idempotency_key:
        saved = await check_idempotency(db, payload.idempotency_key, current_user.id)
        if saved is not None:
            return saved

    account = await get_owned_account(db, payload.account_id, current_user.id)
    if account.balance < payload.amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient funds for FedNow instant transfer",
        )

    # Call Mock Fed Gateway FedNow endpoint
    async with httpx.AsyncClient() as client:
        try:
            fed_res = await client.post(
                f"{FED_GATEWAY_URL}/fed/fednow/transfer",
                json={
                    "debtor_routing": "123456780",
                    "debtor_name": f"{current_user.first_name} {current_user.last_name}".strip() or current_user.email,
                    "debtor_account": account.account_number_last_4,
                    "creditor_routing": payload.creditor_routing,
                    "creditor_name": payload.creditor_name,
                    "creditor_account": payload.creditor_account,
                    "amount_cents": payload.amount,
                    "remittance_info": payload.remittance_info,
                },
                headers={"X-API-KEY": settings.GATEWAY_API_KEY},
                timeout=8.0,
            )
            if fed_res.status_code != 200:
                err = fed_res.json().get("detail", "FedNow transfer rejected")
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err)
            now_data = fed_res.json()
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"FedNow communication failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Federal Reserve FedNow network unavailable",
            )

    client_ip = request.client.host if request.client else "0.0.0.0"
    user_agent = request.headers.get("user-agent", "unknown")

    tx_id = await emit_transactional_event(
        db=db,
        user_id=current_user.id,
        account_id=payload.account_id,
        amount=payload.amount,
        category="Instant Payment",
        merchant=payload.creditor_name,
        transaction_type="fednow",
        transaction_side="DEBIT",
        sender_email=current_user.email,
        recipient_email=f"fednow@{payload.creditor_routing}.fed",
        internal_account_last_4=account.account_number_last_4,
        event_type="transaction.created",
        idempotency_key=payload.idempotency_key or str(uuid.uuid4()),
        ip_address=client_ip,
        user_agent=user_agent,
        status="cleared",
        activity_category="transfer",
        activity_action="sent",
    )

    response_body = {
        "status": "success",
        "end_to_end_id": now_data.get("end_to_end_id"),
        "settlement_timestamp": now_data.get("settlement_timestamp"),
        "transaction_id": tx_id,
    }
    if payload.idempotency_key:
        await complete_idempotency(db, payload.idempotency_key, response_body)

    await db.commit()
    return response_body


@router.post("/transfers/ach")
async def create_ach_transfer(
    payload: ExternalACHTransferRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Executes an outgoing FedACH transfer."""
    if payload.idempotency_key:
        saved = await check_idempotency(db, payload.idempotency_key, current_user.id)
        if saved is not None:
            return saved

    account = await get_owned_account(db, payload.account_id, current_user.id)
    if account.balance < payload.amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient funds for ACH transfer",
        )

    # Call Mock Fed Gateway ACH endpoint
    async with httpx.AsyncClient() as client:
        try:
            fed_res = await client.post(
                f"{FED_GATEWAY_URL}/fed/ach/originate",
                json={
                    "originator_routing": "123456780",
                    "originator_name": f"{current_user.first_name} {current_user.last_name}".strip() or current_user.email,
                    "originator_account": account.account_number_last_4,
                    "receiver_routing": payload.receiver_routing,
                    "receiver_name": payload.receiver_name,
                    "receiver_account": payload.receiver_account,
                    "amount": payload.amount,
                    "sec_code": payload.sec_code,
                    "entry_class": "DEBIT",
                    "payment_description": payload.payment_description,
                },
                headers={"X-API-KEY": settings.GATEWAY_API_KEY},
                timeout=8.0,
            )
            if fed_res.status_code != 200:
                err = fed_res.json().get("detail", "ACH transfer returned by FedACH")
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err)
            ach_data = fed_res.json()
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"ACH communication failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="FedACH network unavailable",
            )

    client_ip = request.client.host if request.client else "0.0.0.0"
    user_agent = request.headers.get("user-agent", "unknown")

    tx_id = await emit_transactional_event(
        db=db,
        user_id=current_user.id,
        account_id=payload.account_id,
        amount=payload.amount,
        category="ACH Transfer",
        merchant=payload.receiver_name,
        transaction_type="ach",
        transaction_side="DEBIT",
        sender_email=current_user.email,
        recipient_email=f"ach@{payload.receiver_routing}.fed",
        internal_account_last_4=account.account_number_last_4,
        event_type="transaction.created",
        idempotency_key=payload.idempotency_key or str(uuid.uuid4()),
        ip_address=client_ip,
        user_agent=user_agent,
        status="cleared",
        activity_category="transfer",
        activity_action="sent",
    )

    response_body = {
        "status": "success",
        "trace_number": ach_data.get("trace_number"),
        "settlement_date": ach_data.get("settlement_date"),
        "transaction_id": tx_id,
    }
    if payload.idempotency_key:
        await complete_idempotency(db, payload.idempotency_key, response_body)

    await db.commit()
    return response_body


