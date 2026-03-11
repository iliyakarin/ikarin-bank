from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.ext.asyncio import AsyncSession
import os
import stripe

from auth_utils import get_db, get_current_user
from services.stripe_service import handle_topup

router = APIRouter(prefix="/stripe", tags=["Stripe"])

stripe.api_key = os.getenv("STRIPE_API_KEY")
stripe.api_base = os.getenv("STRIPE_MOCK_URL", stripe.api_base)
WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

@router.post("/create-checkout-session")
async def create_checkout_session(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user)
):
    try:
        frontend_url = os.getenv("FRONTEND_URL")
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': 'Karin Bank Top-Up',
                    },
                    'unit_amount': payload.get("amount", 1000),  # Default $10
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=f'{frontend_url}/client/stripe/success?session_id={{CHECKOUT_SESSION_ID}}',
            cancel_url=f'{frontend_url}/client/stripe',
            metadata={
                'user_id': user.email
            }
        )
        return {"url": session.url}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/webhook")
async def stripe_webhook(request: Request, stripe_signature: str = Header(None), db: AsyncSession = Depends(get_db)):
    payload = await request.body()
    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Handle the event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        await handle_topup(session, db)
        
    return {"status": "success"}
