from pydantic import BaseModel
from typing import Optional
from datetime import date

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

class VendorInfo(BaseModel):
    id: str
    name: str
    category: str
    email: str

class VendorListResponse(BaseModel):
    vendors: list[VendorInfo]
