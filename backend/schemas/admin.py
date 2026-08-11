from pydantic import BaseModel, Field
from typing import Optional

class SimulationRequest(BaseModel):
    batch_size: Optional[int] = 10
    tps: int
    count: int

class QueryRequest(BaseModel):
    operation: str
    query: str
    params: dict = {}

class AdminCreditRequest(BaseModel):
    """Credits a user's main account from outside the ledger (e.g. payroll)."""
    recipient_email: str
    amount: int = Field(..., gt=0, description="Amount in cents")
    category: str = "income"
    source_name: str = "External Deposit"
    commentary: Optional[str] = None
    idempotency_key: Optional[str] = None
