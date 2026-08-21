from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
import datetime

class P2PTransferRequest(BaseModel):
    recipient_email: str
    amount: int = Field(..., gt=0, description="Amount in cents")
    source_account_id: Optional[int] = None
    idempotency_key: Optional[str] = None
    commentary: Optional[str] = None
    payment_request_id: Optional[int] = None
    subscriber_id: Optional[str] = None

class PaymentRequestCreate(BaseModel):
    target_email: str
    amount: int = Field(..., gt=0, description="Amount in cents")
    purpose: Optional[str] = None

class PaymentRequestCounter(BaseModel):
    amount: int = Field(..., gt=0, description="Amount in cents")

class ScheduledTransferCreate(BaseModel):
    recipient_email: str
    amount: int = Field(..., gt=0, description="Amount in cents")
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
    amount: int = Field(..., gt=0, description="Amount in cents")
    frequency: str
    frequency_interval: Optional[str] = None
    start_date: datetime.datetime
    end_condition: str
    end_date: Optional[datetime.datetime] = None
    target_payments: Optional[int] = None
    year_to_date_total: int = 0
    payments_made: int
    next_run_at: Optional[datetime.datetime] = None
    status: str
    reserve_amount: bool
    funding_account_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)

class TransferRequest(BaseModel):
    account_id: int
    amount: int = Field(..., gt=0, description="Amount in cents")
    category: str
    idempotency_key: Optional[str] = None
    merchant: str = "External Transfer"

# --- Federal Reserve External Payment Rails ---
class WireTransferRequest(BaseModel):
    account_id: int
    amount: int = Field(..., gt=0, description="Amount in cents")
    receiver_routing: str = Field(..., min_length=9, max_length=9, description="9-digit ABA Routing Number")
    receiver_account: str
    receiver_name: str
    payment_reference: Optional[str] = None
    business_function_code: str = "CTR"
    idempotency_key: Optional[str] = None

class FedNowTransferRequest(BaseModel):
    account_id: int
    amount: int = Field(..., gt=0, description="Amount in cents")
    creditor_routing: str = Field(..., min_length=9, max_length=9, description="9-digit ABA Routing Number")
    creditor_account: str
    creditor_name: str
    remittance_info: Optional[str] = None
    idempotency_key: Optional[str] = None

class ExternalACHTransferRequest(BaseModel):
    account_id: int
    amount: int = Field(..., gt=0, description="Amount in cents")
    receiver_routing: str = Field(..., min_length=9, max_length=9, description="9-digit ABA Routing Number")
    receiver_account: str
    receiver_name: str
    payment_description: Optional[str] = "ACH Payment"
    sec_code: str = "PPD"
    idempotency_key: Optional[str] = None
