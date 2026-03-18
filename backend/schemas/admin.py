from pydantic import BaseModel
from typing import Optional

class SimulationRequest(BaseModel):
    batch_size: Optional[int] = 10
    tps: int
    count: int

class QueryRequest(BaseModel):
    operation: str
    query: str
