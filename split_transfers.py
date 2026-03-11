import re
with open("backend/main.py", "r") as f:
    text = f.read()

m = re.search(r"@app\.post\(\"/transfer\"\)[\s\S]*?(?=\n@app\.get\(\"/v1/activity\"\))", text)
if m:
    block = m.group(0).replace("@app.", "@router.")
    text = text.replace(m.group(0) + "\n", "")
    
    header = """from fastapi import APIRouter, Depends, HTTPException, Request
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

logger = logging.getLogger(__name__)
router = APIRouter()

"""
    with open("backend/routers/transfers.py", "w") as f:
        f.write(header + block + "\n")
        
    text = text.replace("app.include_router(admin.router)", "app.include_router(admin.router)\nfrom routers import transfers\napp.include_router(transfers.router)")
    with open("backend/main.py", "w") as f:
        f.write(text)
else:
    print("Failed to match")
