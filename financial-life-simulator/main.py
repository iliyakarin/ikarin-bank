"""Control API + background scheduler for the financial life simulator.

Runs the simulation loop as a background task and exposes a small internal
API for inspection and manual triggering (useful mid-demo, e.g. "watch a
salary deposit land right now" instead of waiting for the 1st/15th).
"""
import asyncio
import contextlib
import logging

from fastapi import FastAPI, HTTPException

from simulator import FinancialLifeSimulator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

sim = FinancialLifeSimulator()


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(sim.run_forever())
    yield
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task
    await sim.client.close()


app = FastAPI(title="Karin Bank Financial Life Simulator", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/status")
async def status():
    return sim.status()


@app.post("/trigger/{event_type}")
async def trigger(event_type: str):
    """Manually fires one simulated event now, ignoring date gating."""
    handlers = {
        "salary": sim.trigger_salary,
        "rent": sim.trigger_rent,
        "insurance": sim.trigger_insurance,
        "purchase": sim.trigger_purchase,
        "p2p": sim.trigger_p2p,
    }
    handler = handlers.get(event_type)
    if not handler:
        raise HTTPException(status_code=404, detail=f"Unknown event_type. Choose from: {list(handlers)}")
    try:
        result = await handler()
    except Exception as e:
        logger.exception("Manual trigger failed for %s", event_type)
        raise HTTPException(status_code=502, detail=f"Upstream API call failed: {e}")
    return {"status": "fired", "event_type": event_type, "result": result}
