import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Vendor Simulator API")

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

VENDORS = [
    {"id": "apple", "name": "Apple Music", "email": "subscriptions@apple.com", "category": "Entertainment"},
    {"id": "pharmacy", "name": "Local Pharmacy", "email": "billing@pharmacy.test", "category": "Healthcare"},
    {"id": "netflix", "name": "Netflix", "email": "billing@netflix.com", "category": "Entertainment"},
    {"id": "gym", "name": "FitZone Gym", "email": "dues@fitzone.test", "category": "Fitness"},
]

@app.get("/vendors")
async def get_vendors():
    return {"vendors": VENDORS}

class WebhookPayload(BaseModel):
    transaction_id: str
    amount: float
    user_email: str
    vendor_email: str

@app.post("/webhook/payment")
async def receive_payment(payload: WebhookPayload):
    # Simulates receiving a scheduled payment
    print(f"[Vendor Simulator] Received {payload.amount} for {payload.vendor_email} from {payload.user_email}")
    return {"status": "accepted"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
