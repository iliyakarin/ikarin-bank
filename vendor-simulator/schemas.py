from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import date, datetime

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
    status: str
    failure_reason: Optional[str] = None

class VendorInfo(BaseModel):
    id: str
    name: str
    category: str
    email: str

class VendorListResponse(BaseModel):
    vendors: List[VendorInfo]

class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    merchant_id: str
    subscriber_id: str
    amount: float
    status: str
    trace_id: str
    failure_reason: Optional[str] = None
    created_at: datetime
