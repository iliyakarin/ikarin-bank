from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uuid

app = FastAPI(title="Stripe Mock Service")

@app.post("/v1/checkout/sessions")
async def create_checkout_session(request: Request):
    """
    Mock Stripe Checkout Session creation.
    """
    # Parse form data which is what stripe python client sends
    form_data = await request.form()
    
    # We will just generate a fake success URL
    success_url = form_data.get("success_url", "http://localhost:3000/dashboard/stripe/success")
    
    session_id = f"cs_test_{uuid.uuid4().hex}"
    
    return JSONResponse({
        "id": session_id,
        "object": "checkout.session",
        "url": success_url.replace("{CHECKOUT_SESSION_ID}", session_id),
        "payment_status": "unpaid",
        "status": "open"
    })

@app.post("/_mock/trigger_webhook")
async def trigger_webhook(request: Request):
    """
    Local testing endpoint to trigger a fake webhook to the backend.
    """
    data = await request.json()
    # In a fully fleshed out mock, this would HTTP POST to the backend /v1/stripe/webhook
    pass
