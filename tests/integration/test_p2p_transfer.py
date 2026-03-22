import sys
import pytest
import asyncio
from unittest.mock import MagicMock, ANY, patch
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
        self.internal_account_last_4 = "1234" # Ensure internal matches for test simplicity
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
        mock_scalars.all.return_value = [sender_account, recipient_account]
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

    # Patch emit_transactional_event in transfer_service to track calls
    with patch("services.transfer_service.emit_transactional_event", new_callable=AsyncMock) as mock_emit:
        mock_emit.return_value = "tx-123" # Mock returning a transaction ID
        
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
    
    # We expect 2 calls to emit_transactional_event (sender and recipient)
    assert mock_emit.call_count == 2
    
    # Verify arguments to emit_transactional_event
    emit_calls = mock_emit.call_args_list
    
    # Check sender emit
    sender_call = next(c for c in emit_calls if c.kwargs['account_id'] == 101)
    assert sender_call.kwargs['amount'] == Decimal("-10.00")
    assert sender_call.kwargs['transaction_side'] == "DEBIT"
    assert sender_call.kwargs['event_type'] == "p2p.sender"
    
    # Check recipient emit
    recipient_call = next(c for c in emit_calls if c.kwargs['account_id'] == 102)
    assert recipient_call.kwargs['amount'] == Decimal("10.00")
    assert recipient_call.kwargs['transaction_side'] == "CREDIT"
    assert recipient_call.kwargs['event_type'] == "p2p.recipient"

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
        mock_scalars.all.return_value = [sender_account, recipient_account]
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
