from fastapi import APIRouter, Depends, HTTPException, Request
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import Session
from database import User, Account, Transaction, Outbox, IdempotencyKey, ScheduledPayment, PaymentRequest
from schemas.transfers import TransferRequest, P2PTransferRequest, PaymentRequestCreate, PaymentRequestCounter, ScheduledTransferCreate, ScheduledPaymentResponse
from auth_utils import get_db, get_current_user
from services.transfer_service import _validate_p2p_transfer, _execute_p2p_balances, _create_p2p_transactions, _create_p2p_outbox_entries, get_vendors, execute_vendor_payment_immediate, _calculate_next_run_at
from activity import emit_activity, emit_transaction_status_update
import datetime
import uuid
import logging
from decimal import Decimal
from sqlalchemy.exc import SQLAlchemyError
from security_checks import check_velocity, check_anomaly

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/transfer")
async def create_transfer(
    transfer: TransferRequest, 
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    tx_id = str(uuid.uuid4())
    client_ip = request.client.host
    user_agent = request.headers.get("user-agent", "unknown")
    try:

        result = await db.execute(select(Account).filter(Account.id == transfer.account_id, Account.user_id == current_user.id))
        account = result.scalars().first()
        if not account:
            raise HTTPException(status_code=403, detail="Account not found or access denied")

        new_tx = Transaction(
            id=tx_id,
            account_id=transfer.account_id,
            amount=transfer.amount,
            category=transfer.category,
            merchant=transfer.merchant,
            status="pending",
            internal_account_last_4=account.account_number_last_4,
            sender_email=current_user.email,
            recipient_email="external@gateway.com" # Generic external recipient
        )
        db.add(new_tx)
        
        # Add to Outbox instead of direct Kafka send
        payload = {
            "transaction_id": tx_id,
            "account_id": transfer.account_id,
            "internal_account_last_4": account.account_number_last_4,
            "internal_reference_id": account.internal_reference_id,
            "amount": transfer.amount,
            "category": transfer.category,
            "merchant": transfer.merchant,
            "transaction_type": "expense",
            "status": "cleared", # legacy /transfer is cleared immediately
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        
        outbox_entry = Outbox(
            event_type="transaction.created",
            payload=payload
        )

        db.add(outbox_entry)
        
        await db.commit()
        return {"status": "success", "transaction_id": tx_id}
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Database transfer failed: {e}")
        raise HTTPException(status_code=500, detail=f"Transaction failed: {str(e)}")








@router.post("/p2p-transfer")
async def create_p2p_transfer(
    transfer: P2PTransferRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    client_ip = request.client.host
    user_agent = request.headers.get("user-agent", "unknown")

    # 1. Idempotency Check
    if transfer.idempotency_key:
        result = await db.execute(select(IdempotencyKey).filter(
            IdempotencyKey.key == transfer.idempotency_key,
            IdempotencyKey.user_id == current_user.id
        ))
        existing_key = result.scalars().first()
        if existing_key:
            return existing_key.response_body

    # 2. Validation & Recipient Lookup
    try:
        recipient = await _validate_p2p_transfer(transfer, current_user, db)
    except HTTPException as e:
        if e.status_code == 404 and "Recipient not found" in str(e.detail):
            # Check for vendor
            vendors = await get_vendors()
            vendor = next((v for v in vendors if v["email"] == transfer.recipient_email), None)
            if vendor:
                # Resolve Sender Account
                sender_account_query = select(Account).filter(Account.user_id == current_user.id)
                if transfer.source_account_id:
                    sender_account_query = sender_account_query.filter(Account.id == transfer.source_account_id)
                else:
                    sender_account_query = sender_account_query.filter(Account.is_main == True)
                    
                result = await db.execute(sender_account_query.with_for_update())
                sender_account = result.scalars().first()
                if not sender_account:
                    raise HTTPException(status_code=404, detail="Source account not found")

                if sender_account.balance < transfer.amount:
                     raise HTTPException(status_code=400, detail="Insufficient funds")

                # Execute Vendor Payment
                sim_resp = await execute_vendor_payment_immediate(
                    vendor["id"], transfer.subscriber_id or "UNKNOWN", transfer.amount
                )

                # Update Balance
                sender_account.balance -= transfer.amount

                # Create Transaction Record
                status_map = {"CLEARED": "cleared", "FAILED": "failed"}
                tx_id = str(uuid.uuid4())
                vendor_tx = Transaction(
                    id=tx_id,
                    account_id=sender_account.id,
                    amount=-transfer.amount,
                    category="Bill Pay",
                    merchant=vendor["name"],
                    status=status_map.get(sim_resp.get("status"), "failed"),
                    transaction_type="expense",
                    transaction_side="DEBIT",
                    failure_reason=sim_resp.get("failure_reason"),
                    commentary=f"Bill Payment to {vendor['name']} (Instant)",
                    internal_account_last_4=sender_account.account_number_last_4,
                    recipient_email=vendor["email"],
                    sender_email=current_user.email,
                    subscriber_id=transfer.subscriber_id,
                    idempotency_key=transfer.idempotency_key or str(uuid.uuid4()),
                    ip_address=client_ip,
                    user_agent=user_agent,
                    created_at=datetime.datetime.now(datetime.timezone.utc)
                )
                db.add(vendor_tx)

                response_body = {"status": "success", "transaction_id": tx_id, "vendor_status": sim_resp.get("status")}
                if transfer.idempotency_key:
                    db.add(IdempotencyKey(
                        key=transfer.idempotency_key,
                        user_id=current_user.id,
                        response_code=200,
                        response_body=response_body
                    ))

                await db.commit()
                return response_body
            else:
                raise # Re-raise original 404
        else:
            raise

    # 2.5 Security Checks
    if not await check_velocity(db, current_user.id):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded: too many transactions in the last minute. Please try again shortly."
        )

    anomaly_flagged = await check_anomaly(db, current_user.id, Decimal(str(transfer.amount)))

    # Validate Payment Request if paying one
    payment_request = None
    if transfer.payment_request_id:
        result = await db.execute(select(PaymentRequest).filter(PaymentRequest.id == transfer.payment_request_id))
        payment_request = result.scalars().first()
        if not payment_request:
            raise HTTPException(status_code=404, detail="Payment request not found")
        # Ensure that the current_user is the target of the request
        if payment_request.target_email != current_user.email:
             raise HTTPException(status_code=403, detail="You are not the target of this payment request")
        if payment_request.status not in ["pending_target", "pending_requester"]:
             raise HTTPException(status_code=400, detail="Payment request is no longer active")
        # Ensure that the amount paid is at least the requested amount
        if transfer.amount < payment_request.amount:
            raise HTTPException(status_code=400, detail=f"Transfer amount must be at least the requested amount (${payment_request.amount})")

    # Resolve Sender Account
    sender_account_query = select(Account).filter(Account.user_id == current_user.id)
    if transfer.source_account_id:
        sender_account_query = sender_account_query.filter(Account.id == transfer.source_account_id)
    else:
        sender_account_query = sender_account_query.filter(Account.is_main == True)
        
    result = await db.execute(sender_account_query)
    resolved_sender_account = result.scalars().first()
    if not resolved_sender_account:
        raise HTTPException(status_code=404, detail="Source account not found or access denied")

    # Resolve Recipient Main Account
    result = await db.execute(select(Account).filter(Account.user_id == recipient.id, Account.is_main == True))
    resolved_recipient_account = result.scalars().first()
    if not resolved_recipient_account:
        raise HTTPException(status_code=404, detail="Recipient main account not found")

    try:
        # 3. Atomic Locking & Balance Verification (ACID)
        sender_account, recipient_account = await _execute_p2p_balances(
            db, resolved_sender_account.id, resolved_recipient_account.id, transfer.amount
        )

        # 4. Create Transaction Records
        tx_id_parent, tx_id_sender, tx_id_recipient = _create_p2p_transactions(
            db,
            sender_account.id,
            recipient_account.id,
            transfer.amount,
            recipient.email,
            current_user.email,
            transfer.idempotency_key,
            client_ip,
            user_agent,
            sender_account_last_4=sender_account.account_number_last_4,
            recipient_account_last_4=recipient_account.account_number_last_4,
            commentary=transfer.commentary,
            payment_request_id=transfer.payment_request_id
        )

        # 5. Create Outbox Entries
        _create_p2p_outbox_entries(
            db,
            sender_account,
            recipient_account,
            transfer.amount,
            current_user.email,
            recipient.email,
            tx_id_parent,
            tx_id_sender,
            tx_id_recipient,
            transfer.commentary
        )

        # Mark payment request as paid if one was linked
        if payment_request:
            payment_request.status = "paid"
            payment_request.updated_at = datetime.datetime.now(datetime.timezone.utc)

        # 6. Finalize Idempotency Key
        response_body = {"status": "success", "transaction_id": tx_id_parent}
        if transfer.idempotency_key:
            db.add(IdempotencyKey(
                key=transfer.idempotency_key,
                user_id=current_user.id,
                response_code=200,
                response_body=response_body
            ))

        # Emit activity events for sender and recipient
        emit_activity(
            db, 
            current_user.id, 
            "p2p", 
            "sent", 
            f"Sent ${float(transfer.amount):.2f} to {recipient.email}", 
            {
                "transaction_id": tx_id_parent,
                "recipient_email": recipient.email,
                "amount": float(transfer.amount),
                "commentary": transfer.commentary,
                "source_account_id": resolved_sender_account.id,
            },
            ip=client_ip,
            user_agent=user_agent
        )
        emit_activity(
            db, 
            recipient.id, 
            "p2p", 
            "received", 
            f"Received ${float(transfer.amount):.2f} from {current_user.email}", 
            {
                "transaction_id": tx_id_parent,
                "sender_email": current_user.email,
                "amount": float(transfer.amount),
                "commentary": transfer.commentary,
            },
            ip=client_ip,
            user_agent=user_agent
        )

        await db.commit()
        return response_body

    except HTTPException:
        await db.rollback()
        raise
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"P2P Transfer failed due to DB error: {e}")
        raise HTTPException(status_code=500, detail="Internal financial processing error")


# --- Payment Requests Endpoints ---

@router.post("/v1/requests/create")
async def create_payment_request(
    request_data: PaymentRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if request_data.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than 0")
    
    if request_data.target_email == current_user.email:
        raise HTTPException(status_code=400, detail="Cannot request money from yourself")
        
    result = await db.execute(select(User).filter(User.email == request_data.target_email))
    target_user = result.scalars().first()
    if not target_user:
        raise HTTPException(status_code=404, detail="Target user not found")

    new_request = PaymentRequest(
        requester_id=current_user.id,
        target_email=request_data.target_email,
        amount=request_data.amount,
        purpose=request_data.purpose,
        status="pending_target"
    )
    
    db.add(new_request)

    emit_activity(db, current_user.id, "p2p", "requested", f"Requested ${float(request_data.amount):.2f} from {request_data.target_email}", {
        "target_email": request_data.target_email,
        "amount": float(request_data.amount),
        "purpose": request_data.purpose,
    })
    await db.commit()
    await db.refresh(new_request)
    
    return {"status": "success", "request_id": new_request.id}


@router.get("/v1/requests")
async def get_payment_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Fetch requests where user is requester or target
    result = await db.execute(select(PaymentRequest).filter(
        (PaymentRequest.requester_id == current_user.id) | 
        (PaymentRequest.target_email == current_user.email)
    ).order_by(PaymentRequest.updated_at.desc()))
    requests = result.scalars().all()
    
    # Enrich with requester info
    result = []
    for req in requests:
        res = await db.execute(select(User).filter(User.id == req.requester_id))
        requester = res.scalars().first()
        result.append({
            "id": req.id,
            "requester_id": req.requester_id,
            "requester_name": f"{requester.first_name} {requester.last_name}" if requester else "Unknown",
            "requester_email": requester.email if requester else "unknown",
            "target_email": req.target_email,
            "amount": float(req.amount),
            "purpose": req.purpose,
            "status": req.status,
            "created_at": req.created_at.isoformat(),
            "updated_at": req.updated_at.isoformat()
        })
        
    return result


@router.post("/v1/requests/{request_id}/counter")
async def counter_payment_request(
    request_id: int,
    counter_data: PaymentRequestCounter,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if counter_data.amount <= 0:
        raise HTTPException(status_code=400, detail="Counter amount must be greater than 0")

    result = await db.execute(select(PaymentRequest).filter(PaymentRequest.id == request_id))
    req = result.scalars().first()
    if not req:
        raise HTTPException(status_code=404, detail="Payment request not found")

    is_requester = req.requester_id == current_user.id
    is_target = req.target_email == current_user.email
    
    if not is_requester and not is_target:
        raise HTTPException(status_code=403, detail="Not authorized to modify this request")
        
    if req.status not in ["pending_target", "pending_requester"]:
        raise HTTPException(status_code=400, detail=f"Request cannot be modified in state: {req.status}")

    # Enforce turns
    if is_target and req.status != "pending_target":
        raise HTTPException(status_code=400, detail="It is not your turn to counter-offer")
    if is_requester and req.status != "pending_requester":
        raise HTTPException(status_code=400, detail="It is not your turn to counter-offer")

    req.amount = counter_data.amount
    # Flip the status depending on who just countered
    req.status = "pending_requester" if is_target else "pending_target"
    req.updated_at = datetime.datetime.now(datetime.timezone.utc)
    
    await db.commit()
    return {"status": "success", "request_id": req.id, "new_amount": float(req.amount), "new_status": req.status}


@router.post("/v1/requests/{request_id}/decline")
async def decline_payment_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(PaymentRequest).filter(PaymentRequest.id == request_id))
    req = result.scalars().first()
    if not req:
        raise HTTPException(status_code=404, detail="Payment request not found")

    if req.requester_id != current_user.id and req.target_email != current_user.email:
        raise HTTPException(status_code=403, detail="Not authorized to modify this request")
        
    if req.status not in ["pending_target", "pending_requester"]:
        raise HTTPException(status_code=400, detail=f"Request cannot be modified in state: {req.status}")

    req.status = "declined"
    req.updated_at = datetime.datetime.now(datetime.timezone.utc)
    
    emit_activity(db, current_user.id, "p2p", "request_declined", f"Declined payment request #{req.id}", {
        "request_id": req.id,
        "amount": float(req.amount),
    })

    # If this request was tied to a transaction (e.g. pending), update its status in ClickHouse
    # Fetch original transaction if exists
    res = await db.execute(select(Transaction).filter(Transaction.payment_request_id == req.id))
    txs = res.scalars().all()
    for tx in txs:
        # Emit a status update for each related transaction record
        from activity import emit_transaction_status_update
        emit_transaction_status_update(
            db,
            transaction_id=str(tx.id),
            account_id=tx.account_id,
            status="declined",
            amount=float(tx.amount),
            category=tx.category,
            merchant=tx.merchant,
            transaction_type=tx.transaction_type,
            transaction_side=tx.transaction_side,
            commentary=f"Payment request #{req.id} declined"
        )

    await db.commit()
    return {"status": "success", "request_id": req.id, "new_status": req.status}

@router.post("/v1/transfers/scheduled")
async def create_scheduled_transfer(
    transfer: ScheduledTransferCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Scheduled Limit check (e.g., max $5000 per scheduled transfer)
    if transfer.amount > 5000:
        raise HTTPException(status_code=400, detail="Amount exceeds maximum scheduled transfer limit of $5000.")

    # Validation: start date in future
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    # Ensure start_date is naive UTC if it comes with tzinfo
    start_date = transfer.start_date
    if start_date.tzinfo is not None:
        start_date = start_date.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    
    # Validation: allow today in user's timezone even if UTC is tomorrow
    if start_date.date() < (now_utc.date() - datetime.timedelta(days=1)):
        raise HTTPException(status_code=400, detail="Start date must be today or in the future.")

    ik = transfer.idempotency_key or str(uuid.uuid4())
    result = await db.execute(select(IdempotencyKey).filter(
        IdempotencyKey.key == ik,
        IdempotencyKey.user_id == current_user.id
    ))
    existing_key = result.scalars().first()
    if existing_key:
        return existing_key.response_body

    try:
        sender_account = None
        if transfer.funding_account_id:
            result = await db.execute(select(Account).filter(
                Account.id == transfer.funding_account_id,
                Account.user_id == current_user.id
            ).with_for_update())
            sender_account = result.scalars().first()
            if not sender_account:
                raise HTTPException(status_code=403, detail="Invalid funding account")
        else:
            # Default to main account
            result = await db.execute(select(Account).filter(Account.user_id == current_user.id, Account.is_main == True).with_for_update())
            sender_account = result.scalars().first()
            if not sender_account:
                result = await db.execute(select(Account).filter(Account.user_id == current_user.id).with_for_update())
                sender_account = result.scalars().first()
                
        if not sender_account:
            raise HTTPException(status_code=404, detail="Account not found")

        # Reserve balance logic
        if transfer.reserve_amount:
            if sender_account.balance < transfer.amount:
                raise HTTPException(status_code=400, detail="Insufficient funds to reserve amount.")
            sender_account.balance -= transfer.amount
            sender_account.reserved_balance += transfer.amount

        # The first run should happen at the start_date provided by user
        next_run = start_date
        
        end_date = transfer.end_date
        if end_date and end_date.tzinfo is not None:
            end_date = end_date.astimezone(datetime.timezone.utc).replace(tzinfo=None)

        new_scheduled_payment = ScheduledPayment(
            user_id=current_user.id,
            recipient_email=transfer.recipient_email,
            amount=transfer.amount,
            frequency=transfer.frequency,
            frequency_interval=transfer.frequency_interval,
            start_date=start_date,
            end_condition=transfer.end_condition,
            end_date=end_date,
            target_payments=transfer.target_payments,
            next_run_at=next_run,
            status="Active",
            idempotency_key=ik,
            reserve_amount=transfer.reserve_amount,
            funding_account_id=sender_account.id,
            subscriber_id=transfer.subscriber_id
        )
        db.add(new_scheduled_payment)
        
        response_body = {"status": "success", "message": "Transfer scheduled successfully."}
        db.add(IdempotencyKey(
            key=ik,
            user_id=current_user.id,
            response_code=200,
            response_body=response_body
        ))
        
        await db.commit()
        await db.refresh(new_scheduled_payment)

        emit_activity(
            db, 
            current_user.id, 
            "scheduled", 
            "setup", 
            f"Scheduled ${float(transfer.amount):.2f} {transfer.frequency} to {transfer.recipient_email}", 
            {
                "scheduled_payment_id": new_scheduled_payment.id,
                "recipient_email": transfer.recipient_email,
                "amount": float(transfer.amount),
                "frequency": transfer.frequency,
                "start_date": str(transfer.start_date),
            },
            ip=request.client.host,
            user_agent=request.headers.get("user-agent")
        )
        await db.commit()
        
        return {"status": "success", "scheduled_payment_id": new_scheduled_payment.id}

    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Scheduled Transfer failed: {e}")
        raise HTTPException(status_code=500, detail="Internal processing error")


@router.get("/v1/transfers/scheduled", response_model=List[ScheduledPaymentResponse])
async def get_scheduled_payments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all scheduled payments for the current user."""
    result = await db.execute(select(ScheduledPayment).filter(
        ScheduledPayment.user_id == current_user.id
    ).order_by(ScheduledPayment.id.desc()))
    payments = result.scalars().all()
    
    return payments

@router.post("/v1/transfers/scheduled/{payment_id}/cancel")
async def cancel_scheduled_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cancel a scheduled payment."""
    result = await db.execute(select(ScheduledPayment).filter(
        ScheduledPayment.id == payment_id,
        ScheduledPayment.user_id == current_user.id
    ))
    payment = result.scalars().first()
    
    if not payment:
        raise HTTPException(status_code=404, detail="Scheduled payment not found")
        
    if payment.status != "Active":
        raise HTTPException(status_code=400, detail=f"Payment is already {payment.status}")
        
    payment.status = "Cancelled"

    emit_activity(db, current_user.id, "scheduled", "cancelled", f"Cancelled scheduled payment #{payment.id}", {
        "scheduled_payment_id": payment.id,
        "recipient_email": payment.recipient_email,
        "amount": float(payment.amount),
    })
    await db.commit()
    
    return {"status": "success", "message": "Scheduled payment cancelled"}


# --- Activity Log Endpoint ---

