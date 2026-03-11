from pydantic import BaseModel
from typing import Optional
import datetime
from decimal import Decimal

class P2PTransferRequest(BaseModel):
    recipient_email: str
    amount: Decimal
    source_account_id: Optional[int] = None
    idempotency_key: Optional[str] = None
    commentary: Optional[str] = None
    payment_request_id: Optional[int] = None
    subscriber_id: Optional[str] = None

class PaymentRequestCreate(BaseModel):
    target_email: str
    amount: Decimal
    purpose: Optional[str] = None

class PaymentRequestCounter(BaseModel):
    amount: Decimal

class ScheduledTransferCreate(BaseModel):
    recipient_email: str
    amount: Decimal
    frequency: str
    frequency_interval: Optional[str] = None
    start_date: datetime.datetime
    end_condition: str
    end_date: Optional[datetime.datetime] = None
    target_payments: Optional[int] = None
    reserve_amount: bool = False
    idempotency_key: Optional[str] = None
    funding_account_id: Optional[int] = None
    subscriber_id: Optional[str] = None

class ScheduledPaymentResponse(BaseModel):
    id: int
    user_id: int
    recipient_email: str
    amount: float
    frequency: str
    frequency_interval: Optional[str] = None
    start_date: datetime.datetime
    end_condition: str
    end_date: Optional[datetime.datetime] = None
    target_payments: Optional[int] = None
    payments_made: int
    next_run_at: Optional[datetime.datetime] = None
    status: str
    reserve_amount: bool
    funding_account_id: Optional[int] = None

    class Config:
        from_attributes = True

class TransferRequest(BaseModel):
    account_id: int
    amount: float
    category: str
    merchant: str
