from pydantic import BaseModel, ConfigDict
from typing import Optional, List

class SubAccountCreate(BaseModel):
    name: str

class SubAccountRename(BaseModel):
    name: str

class InternalTransferRequest(BaseModel):
    from_account_id: int
    to_account_id: int
    amount: int
    commentary: Optional[str] = None

class AccountResponse(BaseModel):
    id: int
    name: str
    balance: int
    reserved_balance: int
    is_main: bool
    routing_number: Optional[str] = None
    masked_account_number: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

class BalanceResponse(BaseModel):
    balance: int
    reserved_balance: int
    user_id: int
    accounts: List[AccountResponse]

class AccountCredentialsResponse(BaseModel):
    routing_number: Optional[str]
    account_number: str
    internal_reference_id: Optional[str]
    masked_account_number: str
