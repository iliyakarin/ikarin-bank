from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uuid

app = FastAPI(title="Deposit Funds Mock Service")

# In-memory store for mock objects
payment_intents = {}

@app.post("/v1/payment_intents")
async def create_payment_intent(request: Request):
    """
    Mock Deposit Funds Payment Intent creation.
    """
    form_data = await request.form()
    amount = form_data.get("amount")
    currency = form_data.get("currency", "usd")
    metadata = {}

    # Parse metadata from form data if present (deposit client sends metadata[key])
    for key, value in form_data.items():
        if key.startswith("metadata[") and key.endswith("]"):
            meta_key = key[9:-1]
            metadata[meta_key] = value
    intent_id = f"pi_{uuid.uuid4().hex}"
    client_secret = f"{intent_id}_secret_{uuid.uuid4().hex}"

    intent = {
        "id": intent_id,
        "object": "payment_intent",
        "amount": int(amount) if amount else 0,
        "currency": currency,
        "status": "requires_payment_method",
        "client_secret": client_secret,
        "metadata": metadata
    }

    payment_intents[intent_id] = intent
    return JSONResponse(intent)

@app.get("/v1/payment_intents/{intent_id}")
async def get_payment_intent(intent_id: str):
    """
    Retrieve a mock Payment Intent.
    """
    if intent_id in payment_intents:
        return JSONResponse(payment_intents[intent_id])
    return JSONResponse({"error": "Payment intent not found"}, status_code=404)

@app.post("/v1/checkout/sessions")
async def create_checkout_session(request: Request):
    """
    Mock Deposit Funds Checkout Session creation.
    """
    form_data = await request.form()
    success_url = form_data.get("success_url", "http://localhost:3000/dashboard/deposit/success")
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
    pass
