import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import datetime
from decimal import Decimal
import sys
import os

# Mock dependencies before any imports
mock_sqlalchemy = MagicMock()
mock_database = MagicMock()

sys.modules['sqlalchemy'] = mock_sqlalchemy
sys.modules['database'] = mock_database

# Define a simple MockTransaction and MockOutbox to capture arguments
class MockTransaction:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        for k, v in kwargs.items():
            setattr(self, k, v)

class MockOutbox:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        for k, v in kwargs.items():
            setattr(self, k, v)

mock_database.Transaction = MockTransaction
mock_database.Outbox = MockOutbox

# Add the backend scripts directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../scripts')))

class TestAddFundsScript(unittest.IsolatedAsyncioTestCase):

    async def test_add_funds_timestamps(self):
        import add_funds

        # Setup mocks
        # Use MagicMock for synchronous methods like .add() and AsyncMock for .execute(), .commit() etc.
        mock_db = MagicMock()
        mock_db.execute = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.flush = AsyncMock()

        add_funds.SessionLocal = MagicMock()
        add_funds.SessionLocal.return_value.__aenter__.return_value = mock_db

        # Mock user result
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.email = "test@example.com"

        # Mock account result
        mock_account = MagicMock()
        mock_account.id = 101
        mock_account.balance = Decimal("100.00")
        mock_account.account_number_last_4 = "1234"

        # Setup db.execute results
        mock_result_user = MagicMock()
        mock_result_user.scalars.return_value.first.return_value = mock_user

        mock_result_account = MagicMock()
        mock_result_account.scalars.return_value.first.return_value = mock_account

        mock_db.execute.side_effect = [mock_result_user, mock_result_account]

        # Run add_funds
        await add_funds.add_funds("test@example.com", Decimal("50.00"))

        # Verify db.add calls
        # There should be 2 calls: one for Transaction, one for Outbox
        self.assertEqual(mock_db.add.call_count, 2)

        # Extract added objects
        added_objects = [call.args[0] for call in mock_db.add.call_args_list]
        transaction = next(obj for obj in added_objects if isinstance(obj, MockTransaction))
        outbox = next(obj for obj in added_objects if isinstance(obj, MockOutbox))

        # Verify timestamps are identical
        self.assertEqual(transaction.created_at, outbox.created_at)
        self.assertEqual(transaction.created_at.isoformat(), outbox.payload["timestamp"])
        self.assertIsInstance(transaction.created_at, datetime.datetime)
        self.assertEqual(transaction.created_at.tzinfo, datetime.timezone.utc)

if __name__ == '__main__':
    unittest.main()
