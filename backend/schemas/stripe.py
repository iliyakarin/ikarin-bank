from pydantic import BaseModel
from typing import Optional, Dict, Any

class CheckoutSessionCreate(BaseModel):
    amount: int  # in cents
    currency: str = "usd"
    mode: str = "payment"  # 'payment' or 'subscription'
    success_url: str
    cancel_url: str

class CheckoutSessionResponse(BaseModel):
    id: str
    url: str

class PortalSessionCreate(BaseModel):
    return_url: str

class PortalSessionResponse(BaseModel):
    url: str

class PaymentIntentCreate(BaseModel):
    amount: int  # in cents
    currency: str = "usd"
    metadata: Optional[Dict[str, Any]] = None

class PaymentIntentResponse(BaseModel):
    client_secret: str
    id: str
