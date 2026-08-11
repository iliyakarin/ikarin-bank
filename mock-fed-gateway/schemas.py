from pydantic import BaseModel, Field
from typing import Optional

class ACHOriginateRequest(BaseModel):
    routing_number: str = Field(..., min_length=9, max_length=9)
    account_number: str
    amount: float
    type: str = "ACH"

class StatusResponse(BaseModel):
    status: str
    message: Optional[str] = None
    error_code: Optional[str] = None
