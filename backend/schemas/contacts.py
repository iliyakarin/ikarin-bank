from pydantic import BaseModel
from typing import Optional
import datetime

class ContactCreate(BaseModel):
    contact_name: str
    contact_email: Optional[str] = None
    contact_type: str = "karin" # karin, merchant, bank
    # Merchant fields
    merchant_id: Optional[str] = None
    subscriber_id: Optional[str] = None
    # Bank fields
    bank_name: Optional[str] = None
    routing_number: Optional[str] = None
    account_number: Optional[str] = None

class ContactResponse(BaseModel):
    id: int
    user_id: int
    contact_name: str
    contact_email: Optional[str] = None
    contact_type: str
    merchant_id: Optional[str] = None
    subscriber_id: Optional[str] = None
    bank_name: Optional[str] = None
    routing_number: Optional[str] = None
    account_number: Optional[str] = None
    created_at: datetime.datetime

    class Config:
        from_attributes = True

class ContactUpdate(BaseModel):
    contact_name: str
    contact_email: Optional[str] = None
    # Allow updating metadata too
    merchant_id: Optional[str] = None
    subscriber_id: Optional[str] = None
    bank_name: Optional[str] = None
    routing_number: Optional[str] = None
    account_number: Optional[str] = None
