from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, List


def _luhn_check(card_number: str) -> bool:
    """Validate card number using Luhn algorithm."""
    try:
        digits = [int(d) for d in card_number]
        checksum = sum(digits[::-2]) + sum(
            sum(divmod(d * 2, 10)) for d in digits[-2::-2]
        )
        return checksum % 10 == 0
    except (ValueError, IndexError):
        return False


class CheckoutSessionCreate(BaseModel):
    amount: int = Field(..., gt=0, description="Amount in cents")
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
    amount: int = Field(..., gt=0, description="Amount in cents")
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
    card_number: str = Field(..., min_length=13, max_length=19, pattern=r"^\d+$")
    exp_month: str = Field(..., min_length=2, max_length=2, pattern=r"^\d+$")
    exp_year: str = Field(..., min_length=2, max_length=4, pattern=r"^\d+$")
    cvc: str = Field(..., min_length=3, max_length=4, pattern=r"^\d+$")
    name: str = Field(..., min_length=1, max_length=100)

    @field_validator("card_number")
    @classmethod
    def validate_card_number(cls, v: str) -> str:
        if not _luhn_check(v):
            raise ValueError("Card number failed Luhn check")
        return v

    @field_validator("exp_month")
    @classmethod
    def validate_exp_month(cls, v: str) -> str:
        month = int(v)
        if month < 1 or month > 12:
            raise ValueError("Invalid expiration month")
        return v


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
    amount: Optional[int] = None
    current_period_end: Optional[str] = None
    status: Optional[str] = None

