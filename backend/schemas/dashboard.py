from pydantic import BaseModel, ConfigDict
from typing import List, Dict, Any, Optional
from datetime import datetime

class ChartDataPoint(BaseModel):
    date: str
    amount: int

class RecentTransaction(BaseModel):
    id: str
    merchant: str
    amount: int
    category: str
    status: str
    created_at: datetime
    transaction_side: str

class DashboardMetrics(BaseModel):
    total_balance: int
    monthly_spending: int
    monthly_income: int
    spending_change_pct: float
    income_change_pct: float
    recent_transactions: List[RecentTransaction]
    chart_data: List[ChartDataPoint]
    category_distribution: Dict[str, int]
