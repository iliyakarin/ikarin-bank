from pydantic import BaseModel, root_validator
from decimal import Decimal
from typing import Optional, Dict, Any

class PaymentIntentCreate(BaseModel):
    amount: int  # integer cents
    currency: str = "usd"
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class PaymentMethodCreate(BaseModel):
    card_number: str
    exp_month: str
    exp_year: str
    cvc: str
    name: str

class PaymentIntentConfirm(BaseModel):
    payment_method: str

class DepositCard(BaseModel):
    last4: str
    brand: str

class PaymentMethodResponse(BaseModel):
    id: str
    object: str = "payment_method"
    type: str = "card"
    card: DepositCard

class PaymentIntentResponse(BaseModel):
    id: str
    object: str = "payment_intent"
    amount: int
    currency: str
    status: str
    client_secret: str

class SubscriptionResponse(BaseModel):
    active: bool
    plan_name: Optional[str] = None
    amount: Optional[float] = None
    current_period_end: Optional[str] = None
    status: Optional[str] = None
