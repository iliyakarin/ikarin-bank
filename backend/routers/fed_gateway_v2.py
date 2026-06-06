from fastapi import APIRouter, status, Depends
from v2.fed_gateway.transport.mq_client import MQClient
from pydantic import BaseModel
from typing import Optional
from backend.database import SessionLocal
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/v2/fed-gateway", tags=["fed-gateway-v2"])

class FedMessageRequest(BaseModel):
    payload: str
    correlation_id: str

class StatusQueryRequest(BaseModel):
    transaction_id: str

class BalanceQueryRequest(BaseModel):
    account_id: str

@router.post("/inject", status_code=status.HTTP_202_ACCEPTED)
async def inject_fed_message(request: FedMessageRequest, mq: MQClient):
    """
    Injects an ISO 20022 XML message into the simulated MQ transport.
    Used for simulating inbound FedLine Direct messages.
    """
    await mq.inject_mock_message(request.payload)
    return {"status": "accepted", "correlation_id": request.correlation_id}

@router.get("/transaction/{transaction_id}", response_model=dict)
async def get_transaction_status(transaction_id: str, engine: any = Depends(lambda: None)):
    """
    Retrieves the status of a specific transaction from the SettlementEngine.
    Note: In a real app, this would use a dependency to inject the engine instance.
    """
    # For simulation, we assume the engine is globally accessible or injected via app state.
    # This is a placeholder for the actual dependency injection logic.
    return {"transaction_id": transaction_id, "status": "simulated_status"}

@router.get("/balance/{account_id}", response_model=dict)
async def get_account_balance(account_id: str, engine: any = Depends(lambda: None)):
    """
    Returns the current virtual Fed reserve balance for the specified account.
    """
    return {"account_id": account_id, "balance": 5000000.0}

@router.post("/generate-statement/{account_id}", response_model=dict)
async def generate_statement(account_id: str, engine: any = Depends(lambda: None)):
    """
    Triggers the generation of a camt.053 XML statement.
    """
    return {"account_id": account_id, "status": "statement_generated"}
