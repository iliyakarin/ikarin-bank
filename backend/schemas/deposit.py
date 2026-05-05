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
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class PaymentIntentResponse(BaseModel):
    id: str
    object: str = "payment_intent"
    amount: int
    currency: str
    status: str
    client_secret: str

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
    object: str = "payment_method"
    type: str = "card"
    card: CardResponse

class PaymentIntentConfirm(BaseModel):
    payment_method: str

class SubscriptionResponse(BaseModel):
    active: bool
    plan_name: Optional[str] = None
    amount: Optional[float] = None
    current_period_end: Optional[str] = None
    status: Optional[str] = None
