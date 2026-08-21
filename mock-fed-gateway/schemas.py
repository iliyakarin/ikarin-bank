from datetime import datetime, date
from typing import Optional, List, Union, Dict, Any
from pydantic import BaseModel, Field

# --- Directory & Districts ---
class DistrictOut(BaseModel):
    id: int
    code: str
    name: str
    district_letter: str
    head_office_city: str
    head_office_state: str
    routing_prefix_ranges: Optional[List[str]] = None

    model_config = {"from_attributes": True}

class InstitutionOut(BaseModel):
    routing_number: str
    name: str
    short_name: str
    district_id: int
    office_code: str
    servicing_frb_number: str
    city: str
    state: str
    zip_code: str
    phone: str
    fedach_participant: bool
    fedwire_participant: bool
    fednow_participant: bool
    status: str

    model_config = {"from_attributes": True}

class DirectorySearchResponse(BaseModel):
    total: int
    institutions: List[InstitutionOut]

class RoutingLookupResponse(BaseModel):
    valid: bool
    routing_number: str
    formatted: str
    institution: Optional[InstitutionOut] = None
    district: Optional[DistrictOut] = None
    errors: List[str] = []

class BankSimple(BaseModel):
    name: str
    routing_number: str

class BankListResponse(BaseModel):
    banks: List[BankSimple]

# --- FedACH ---
class ACHOriginateRequest(BaseModel):
    originator_routing: Optional[str] = Field(None, min_length=9, max_length=9)
    originator_name: Optional[str] = "Originating Institution"
    originator_account: Optional[str] = "100001"
    receiver_routing: Optional[str] = Field(None, min_length=9, max_length=9)
    routing_number: Optional[str] = Field(None, min_length=9, max_length=9)  # For backward compatibility
    receiver_name: Optional[str] = "Receiver Customer"
    receiver_account: Optional[str] = None
    account_number: Optional[str] = None  # For backward compatibility
    amount: Union[int, float] = Field(..., gt=0, description="Amount in cents (int) or dollars (float)")
    sec_code: str = "PPD"
    entry_class: str = "DEBIT"
    payment_description: Optional[str] = "ACH Payment"
    type: str = "ACH"

class ACHTransactionResponse(BaseModel):
    id: str
    trace_number: str
    sec_code: str
    originator_routing: str
    receiver_routing: str
    amount_cents: int
    entry_class: str
    status: str  # SETTLED, RETURNED, PENDING
    return_code: Optional[str] = None
    return_reason: Optional[str] = None
    settlement_date: date
    message: Optional[str] = None

    model_config = {"from_attributes": True}

class ACHBatchEntry(BaseModel):
    receiver_routing: str
    receiver_name: str
    receiver_account: str
    amount: Union[int, float]
    sec_code: str = "PPD"
    entry_class: str = "DEBIT"
    payment_description: Optional[str] = ""

class ACHBatchRequest(BaseModel):
    originator_routing: str
    originator_name: str
    originator_account: str
    entries: List[ACHBatchEntry]

class ACHBatchResponse(BaseModel):
    batch_id: str
    total_entries: int
    settled_count: int
    returned_count: int
    total_debits_cents: int
    total_credits_cents: int
    transactions: List[ACHTransactionResponse]

# --- Fedwire (RTGS) ---
class FedwireOriginateRequest(BaseModel):
    sender_routing: str = Field(..., min_length=9, max_length=9)
    sender_name: str
    sender_account: str
    receiver_routing: str = Field(..., min_length=9, max_length=9)
    receiver_name: str
    receiver_account: str
    amount_cents: int = Field(..., gt=0)
    business_function_code: str = "CTR"  # CTR, BTR, DEP, DRC
    charge_details: str = "OUR"
    payment_reference: Optional[str] = None

class FedwireTransferResponse(BaseModel):
    imad: str
    omad: str
    business_function_code: str
    sender_routing: str
    receiver_routing: str
    amount_cents: int
    status: str  # SETTLED, REJECTED, PENDING
    rejection_reason: Optional[str] = None
    settlement_timestamp: datetime

    model_config = {"from_attributes": True}

# --- FedNow (Instant Payments) ---
class FedNowTransferRequest(BaseModel):
    end_to_end_id: Optional[str] = None
    instruction_id: Optional[str] = None
    debtor_routing: str = Field(..., min_length=9, max_length=9)
    debtor_name: str
    debtor_account: str
    creditor_routing: str = Field(..., min_length=9, max_length=9)
    creditor_name: str
    creditor_account: str
    amount_cents: int = Field(..., gt=0)
    remittance_info: Optional[str] = None

class FedNowRFPRequest(BaseModel):
    rfp_id: Optional[str] = None
    debtor_routing: str
    debtor_name: str
    creditor_routing: str
    creditor_name: str
    amount_cents: int
    expiry_hours: int = 48
    remittance_info: Optional[str] = None

class FedNowTransferResponse(BaseModel):
    end_to_end_id: str
    instruction_id: str
    status: str  # ACCP, RJCT, PEND
    status_reason_code: Optional[str] = None
    status_reason_description: Optional[str] = None
    amount_cents: int
    settlement_timestamp: datetime

    model_config = {"from_attributes": True}

# --- Master Accounts & Settlement ---
class MasterAccountResponse(BaseModel):
    account_number: str
    routing_number: str
    currency: str
    balance_cents: int
    daylight_overdraft_limit_cents: int
    available_liquidity_cents: int
    status: str
    updated_at: datetime

    model_config = {"from_attributes": True}

class MasterAccountAdjustRequest(BaseModel):
    routing_number: str
    adjustment_cents: int  # positive to credit, negative to debit
    reason: str

class DailyStatementResponse(BaseModel):
    routing_number: str
    statement_date: date
    opening_balance_cents: int
    closing_balance_cents: int
    ach_debits_cents: int
    ach_credits_cents: int
    fedwire_debits_cents: int
    fedwire_credits_cents: int
    fednow_debits_cents: int
    fednow_credits_cents: int
    total_transactions_count: int

# --- Generic & Health ---
class StatusResponse(BaseModel):
    status: str
    message: Optional[str] = None
    error_code: Optional[str] = None

class HealthResponse(BaseModel):
    status: str
    service: str = "mock-fed-gateway"
    version: str = "2.0.0"
    districts_count: int
    institutions_count: int
