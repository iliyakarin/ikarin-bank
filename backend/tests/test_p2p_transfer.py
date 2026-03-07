import sys
import pytest
import asyncio
from unittest.mock import MagicMock, ANY
from decimal import Decimal

# Helper to create a mock request
def create_mock_request():
    mock_request = MagicMock()
    mock_request.client.host = "127.0.0.1"
    mock_request.headers.get.return_value = "TestAgent"
    return mock_request

# Use simple object for Account to ensure attribute updates work reliably
class MockAccount:
    def __init__(self, id, user_id, balance):
        self.id = id
        self.user_id = user_id
        self.balance = balance
        self.account_number_last_4 = "1234"
        self.is_main = True

@pytest.mark.asyncio
async def test_p2p_transfer_success(mock_fastapi_dependency):
    main_module = mock_fastapi_dependency

    # Setup Data
    sender = MagicMock()
    sender.id = 1
    sender.email = "sender@example.com"

    recipient = MagicMock()
    recipient.id = 2
    recipient.email = "recipient@example.com"

    sender_account = MockAccount(101, 1, Decimal("100.00"))
    recipient_account = MockAccount(102, 2, Decimal("50.00"))

    from unittest.mock import AsyncMock
    mock_db = MagicMock()
    mock_db.execute = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.rollback = AsyncMock()

    account_iterator = iter([sender_account, recipient_account] * 10)
    call_idx_p2p = [0]
    
    def execute_side_effect(stmt, *args, **kwargs):
        idx = call_idx_p2p[0]
        call_idx_p2p[0] += 1
        
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [101, 102]
        mock_result.scalar.return_value = 0
        mock_result.scalars.return_value = mock_scalars

        if idx == 0: # Idempotency
            mock_scalars.first.return_value = None
        elif idx == 1: # User lookup
            mock_scalars.first.return_value = recipient
        else: # Account lookups
            mock_scalars.first.return_value = next(account_iterator, None)
        return mock_result

    mock_db.execute.side_effect = execute_side_effect

    transfer_req = main_module.P2PTransferRequest(
        recipient_email="recipient@example.com",
        amount=Decimal("10.00"),
        idempotency_key="unique-key-123"
    )

    mock_request = create_mock_request()

    # Execute
    response = await main_module.create_p2p_transfer(
        transfer=transfer_req,
        request=mock_request,
        db=mock_db,
        current_user=sender
    )

    # Verify
    assert response["status"] == "success"
    assert response["transaction_id"] is not None
    assert sender_account.balance == Decimal("90.00")
    assert recipient_account.balance == Decimal("60.00")
    assert mock_db.add.call_count >= 5
    mock_db.commit.assert_called_once()

    # Verify arguments to add
    added_objects = [call[0][0] for call in mock_db.add.call_args_list]

    # Check Transactions
    # main_module.Transaction might be a MagicMock object, not a type, if mocked improperly or if we are unlucky.
    # isinstance(x, MagicMock) works if x is an instance of MagicMock (which it is).
    # BUT `main_module.Transaction` is the class.
    # If `backend.database` is mocked, `Transaction` is a Mock object acting as a class.
    # Creating an instance `Transaction(...)` returns a Mock object (the instance).
    # So `isinstance(instance, ClassMock)` might fail if ClassMock is not a type.

    # Instead of isinstance, let's check by property or just iterate and check duck typing.
    txs = []
    outbox = []

    # We can check `obj.__class__` or simply check properties.
    # Since Transaction and Outbox are created via `main_module.Transaction(...)`,
    # `obj` is the return value of that call.

    # If `main_module.Transaction` is a MagicMock, calling it returns a child MagicMock.

    # Let's verify by checking attributes that are specific.
    for obj in added_objects:
        # Transaction has 'transaction_side'
        # Outbox has 'event_type'

        # MagicMock objects have all attributes, so we need to be careful.
        # But we can check if `obj` was created by `main_module.Transaction`.

        # Or simpler:
        # We can just check `obj.amount` exists and is Decimal for transaction.
        # But Outbox has payload dict which has amount.

        # Let's inspect the `spec` if available, or just guess.

        # Actually, `main_module.Transaction` IS the constructor.
        # calling it returns `obj`.
        # So `obj` is a child of `main_module.Transaction`.
        # But `isinstance` checks against TYPE.

        # Let's try to identify by 'event_type' for outbox.
        # If 'event_type' is set, it's Outbox.
        # If 'transaction_side' is set, it's Transaction.
        # Note: Transaction has 'transaction_side'. Outbox has 'event_type'.

        # However, getting an attribute on a MagicMock creates it.
        # So `obj.event_type` will exist for Transaction too!

        # We can check what call created it? No.

        # Let's check `_spec_class` or similar? No.

        # Let's rely on the fact that we set specific values.
        # Transaction: amount is Decimal.
        # Outbox: payload is Dict.

        # obj.amount is Decimal -> Transaction
        # obj.payload is Dict -> Outbox

        # But again, accessing obj.amount on Outbox mock returns a Mock.

        # WAIT. We are running in `mock_fastapi_dependency`.
        # `mock_database` is patching `backend.database`.
        # `mock_database.Transaction` is a MagicMock.
        # `mock_database.Outbox` is a MagicMock.

        # When `main.py` calls `Transaction(...)`, it returns a NEW MagicMock.
        # We can't easily distinguish them unless we trace back to parent.

        # BUT, we can check arguments passed to `db.add()`.
        # `db.add(obj)`.

        # We can check the `mock_calls` on `main_module.Transaction`.
        pass

    # Verify Transaction creation calls
    assert main_module.Transaction.call_count == 2

    # Check args passed to Transaction constructor
    tx_calls = main_module.Transaction.call_args_list
    amounts = sorted([call.kwargs['amount'] for call in tx_calls])
    assert amounts[0] == Decimal("-10.00")
    assert amounts[1] == Decimal("10.00")

    # Verify Outbox creation calls
    assert main_module.Outbox.call_count >= 2
    outbox_calls = main_module.Outbox.call_args_list
    events = sorted([call.kwargs['event_type'] for call in outbox_calls])
    assert events == ["p2p.recipient", "p2p.sender"]

@pytest.mark.asyncio
async def test_p2p_transfer_insufficient_funds(mock_fastapi_dependency):
    main_module = mock_fastapi_dependency

    sender = MagicMock()
    sender.id = 1
    sender.email = "sender@example.com"

    recipient = MagicMock()
    recipient.id = 2
    recipient.email = "recipient@example.com"

    sender_account = MockAccount(101, 1, Decimal("5.00")) 
    recipient_account = MockAccount(102, 2, Decimal("50.00"))

    from unittest.mock import AsyncMock
    mock_db = MagicMock()
    mock_db.execute = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.rollback = AsyncMock()

    account_iterator = iter([sender_account, recipient_account] * 10)
    call_idx_p2p = [0]
    
    def execute_side_effect(stmt, *args, **kwargs):
        idx = call_idx_p2p[0]
        call_idx_p2p[0] += 1
        
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [101, 102]
        mock_result.scalar.return_value = 0
        mock_result.scalars.return_value = mock_scalars

        if idx == 0: # Idempotency
            mock_scalars.first.return_value = None
        elif idx == 1: # User lookup
            mock_scalars.first.return_value = recipient
        else: # Account lookups
            mock_scalars.first.return_value = next(account_iterator, None)
        return mock_result

    mock_db.execute.side_effect = execute_side_effect

    transfer_req = main_module.P2PTransferRequest(
        recipient_email="recipient@example.com",
        amount=Decimal("10.00"),
        idempotency_key="unique-key-456"
    )

    mock_request = create_mock_request()

    try:
        await main_module.create_p2p_transfer(
            transfer=transfer_req,
            request=mock_request,
            db=mock_db,
            current_user=sender
        )
        pytest.fail("Should have raised HTTPException")
    except Exception as e:
        if hasattr(e, "status_code"):
             assert e.status_code == 400
        else:
             raise e

    mock_db.rollback.assert_called()
