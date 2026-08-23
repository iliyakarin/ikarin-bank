import ast
import pathlib
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

ADMIN_ROUTER = pathlib.Path("backend/routers/admin.py")
ADMIN_SERVICE = pathlib.Path("backend/services/admin_service.py")

def _names_defined(source: str) -> set[str]:
    tree = ast.parse(source)
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }

def test_admin_router_endpoints_present():
    names = _names_defined(ADMIN_ROUTER.read_text())
    assert "get_banking_metrics" in names
    assert "get_bank_wide_transactions" in names
    assert "get_fed_reserves" in names
    assert "get_fed_daily_statement" in names
    assert "get_fed_status" in names
    assert "trigger_fed_settlement_sync" in names

def test_admin_service_functions_present():
    names = _names_defined(ADMIN_SERVICE.read_text())
    assert "get_system_metrics" in names
    assert "get_all_transactions_for_admin" in names
    assert "compliance_delete_user" in names

@pytest.mark.asyncio
async def test_get_system_metrics_structure():
    from services.admin_service import get_system_metrics

    # Mock db session
    mock_result = MagicMock()
    mock_result.scalar.return_value = 5000000  # $50,000.00
    mock_result.all.return_value = [("2026-08-22", 5)]
    mock_result.scalars.return_value.all.return_value = []

    mock_db = AsyncMock()
    mock_db.execute.return_value = mock_result

    with patch("services.admin_service.execute_ch_query", new_callable=AsyncMock) as mock_ch:
        # Mock ClickHouse responses
        mock_ch.return_value.result_rows = [[15, 125000]]

        metrics = await get_system_metrics(mock_db)

        assert "totalVolume" in metrics
        assert "transactionCount" in metrics
        assert "totalBalance" in metrics
        assert "activeUsers" in metrics
        assert "avgTransactionSize" in metrics
        assert "topTransactions" in metrics
        assert "hourlyVolume" in metrics
        assert "merchantStats" in metrics
        assert "userGrowth" in metrics

        assert metrics["totalBalance"] == 5000000
        assert metrics["transactionCount"] == 15
        assert len(metrics["hourlyVolume"]) == 24
