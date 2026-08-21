import pytest
from v2.fed_gateway.engine.settlement import SettlementEngine, SettlementStatus

@pytest.mark.asyncio
async def test_fednow_instant_settlement_success():
    """Verifies that FedNow payments are processed instantly with success."""
    engine = SettlementEngine()
    tx_id = "FEDNOW-1"
    amount = 1000.0
    
    result = await engine.process_fednow_payment(tx_id, amount)
    
    assert result["status"] == SettlementStatus.SETTLED.value
    assert result["transaction_id"] == tx_id
    assert engine.get_account_balance() == 5000000.0 - 1000.0

@pytest.mark.asyncio
async def test_fednow_insufficient_funds():
    """Verifies that FedNow payments fail if they exceed available reserves."""
    engine = SettlementEngine()
    tx_id = "FEDNOW-FAIL"
    amount = 6000000.0  # Exceeds 5M reserves
    
    result = await engine.process_fednow_payment(tx_id, amount)
    
    assert result["status"] == SettlementStatus.REJECTED.value
    assert "Insufficient liquidity" in result["reason"]

@pytest.mark.asyncio
async def test_fedwire_daylight_overdraft_success():
    """Verifies that Fedwire allows payments within the overdraft limit."""
    engine = SettlementEngine(max_overdraft_limit=1000000.0)
    tx_id = "FEDWIRE-1"
    amount = 5500000.0  # 5M reserves + 0.5M overdraft
    
    result = await engine.process_fedwire_payment(tx_id, amount)
    
    assert result["status"] == SettlementStatus.SETTLED.value
    assert engine.get_account_balance() == 5000000.0 - 5500000.0 # Becomes negative

@pytest.mark.asyncio
async def test_fedwire_exceed_overdraft_limit():
    """Verifies that Fedwire fails if amount exceeds reserves + overdraft limit."""
    engine = SettlementEngine(max_overdraft_limit=1000000.0)
    tx_id = "FEDWIRE-FAIL"
    amount = 7000000.0  # Exceeds 5M + 1M
    
    result = await engine.process_fedwire_payment(tx_id, amount)
    
    assert result["status"] == SettlementStatus.REJECTED.value
    assert "Exceeds daylight overdraft limit" in result["reason"]

@pytest.mark.asyncio
async def test_invalid_amount():
    """Verifies that zero or negative amounts are rejected."""
    engine = SettlementEngine()
    tx_id = "NEG-1"
    
    result = await engine.process_fednow_payment(tx_id, -50.0)
    assert result["status"] == SettlementStatus.REJECTED.value
    
    result = await engine.process_fedwire_payment(tx_id, 0.0)
    assert result["status"] == SettlementStatus.REJECTED.value
