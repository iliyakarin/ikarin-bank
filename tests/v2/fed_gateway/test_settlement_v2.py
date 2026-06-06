import unittest
import asyncio
from v2.fed_gateway.engine.settlement import SettlementEngine, SettlementStatus

class TestSettlementEngine(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Initialize engine with controlled values for testing
        self.engine = SettlementEngine(max_overdraft_limit=1000.0, initial_reserve_balance=5000.0)

    async def test_process_fednow_payment_success(self):
        transaction_id = "FEDNOW-123"
        amount = 100.0
        
        result = self.engine.process_fednow_payment(transaction_id, amount)
        
        self.assertEqual(result["status"], SettlementStatus.SETTLED.value)
        self.assertEqual(self.engine.get_account_balance(), 4900.0)

    async def test_process_fednow_payment_insufficient_liquidity(self):
        transaction_id = "FEDNOW-ERR"
        amount = 10000.0  # Exceeds 5000.0 reserve
        
        result = self.engine.process_fednow_payment(transaction_id, amount)
        
        self.assertEqual(result["status"], SettlementStatus.REJECTED.value)
        self.assertEqual(result["reason"], "Insufficient liquidity in Fed account")

    async def test_process_fedwire_payment_success(self):
        transaction_id = "FEDWIRE-123"
        amount = 5500.0 # Within 5000 + 1000 overdraft limit
        
        result = self.engine.process_fedwire_payment(transaction_id, amount)
        
        self.assertEqual(result["status"], SettlementStatus.SETTLED.value)
        # Balance becomes 5000 - 5500 = -500 (allowed via daylight overdraft)
        self.assertEqual(self.engine.get_account_balance(), -500.0)

    async def test_process_fedwire_payment_exceeds_overdraft(self):
        transaction_id = "FEDWIRE-FAIL"
        amount = 7000.0 # Exceeds 5000 + 1000 limit
        
        result = self.engine.process_fedwire_payment(transaction_id, amount)
        
        self.assertEqual(result["status"], SettlementStatus.REJECTED.value)
        self.assertEqual(result["reason"], "Exceeds daylight overdraft limit")

    async def test_process_invalid_amount(self):
        transaction_id = "INVALID-AMT"
        amount = -50.0
        
        # Test both FedNow and Fedwire
        result_now = self.engine.process_fednow_payment(transaction_id, amount)
        result_wire = self.engine.process_fedwire_payment(transaction_id, amount)
        
        self.assertEqual(result_now["status"], SettlementStatus.REJECTED.value)
        self.assertEqual(result_wire["status"], SettlementStatus.REJECTED.value)

if __name__ == "__main__":
    unittest.main()
