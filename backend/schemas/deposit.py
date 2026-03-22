from pydantic import BaseModel
from typing import Optional, Dict, Any, List

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
    status: Optional[str] = "requires_payment_method"
    amount: Optional[int] = None
    currency: Optional[str] = "usd"

class PaymentIntentFulfill(BaseModel):
    id: str

class PaymentMethodCreate(BaseModel):
    card_number: str
    exp_month: str
    exp_year: str
    cvc: str
    name: str

class CardResponse(BaseModel):
    last4: str
    brand: str

class PaymentMethodResponse(BaseModel):
    id: str
    card: CardResponse

class PaymentIntentConfirm(BaseModel):
    payment_method: str
