from pydantic import BaseModel
from typing import Optional

class SimulationRequest(BaseModel):
    batch_size: Optional[int] = 10

class QueryRequest(BaseModel):
    operation: str
    query: str
