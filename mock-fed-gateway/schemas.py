from pydantic import BaseModel, Field
from typing import Optional
from datetime import date

class ACHOriginateRequest(BaseModel):
    routing_number: str = Field(..., min_length=9, max_length=9)
    account_number: str
    amount: float
    type: str = "ACH"

class BillPayValidationRequest(BaseModel):
    merchant_id: str
    subscriber_id: str

class BillPayExecuteRequest(BaseModel):
    merchant_id: str
    subscriber_id: str
    amount: float

class StatusResponse(BaseModel):
    status: str
    message: Optional[str] = None
    error_code: Optional[str] = None

class BillPayExecuteResponse(BaseModel):
    trace_id: str
    settlement_date: date
