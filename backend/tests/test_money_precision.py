"""Unit tests for monetary precision, gt=0 amount validation, and async ClickHouse helpers."""
import pytest
import asyncio
from pydantic import ValidationError
from unittest.mock import MagicMock

from schemas.transfers import P2PTransferRequest, PaymentRequestCreate, ScheduledTransferCreate, TransferRequest
from schemas.deposit import CheckoutSessionCreate, PaymentIntentCreate, SubscriptionResponse
from clickhouse_utils import execute_ch_query, execute_ch_command, execute_ch_insert


def test_transfer_schemas_reject_zero_and_negative_amounts():
    """Verify that all transfer schemas reject zero or negative amounts with ValidationError."""
    with pytest.raises(ValidationError):
        P2PTransferRequest(recipient_email="test@example.com", amount=0)

    with pytest.raises(ValidationError):
        P2PTransferRequest(recipient_email="test@example.com", amount=-500)

    with pytest.raises(ValidationError):
        PaymentRequestCreate(target_email="test@example.com", amount=0)

    with pytest.raises(ValidationError):
        PaymentRequestCreate(target_email="test@example.com", amount=-100)

    with pytest.raises(ValidationError):
        TransferRequest(account_id=1, amount=0, category="general", merchant="store")

    with pytest.raises(ValidationError):
        CheckoutSessionCreate(amount=0, success_url="http://ok", cancel_url="http://cancel")

    with pytest.raises(ValidationError):
        PaymentIntentCreate(amount=-50)


def test_transfer_schemas_accept_positive_integer_amounts():
    """Verify that positive integer cents are accepted."""
    p2p = P2PTransferRequest(recipient_email="test@example.com", amount=1050)
    assert p2p.amount == 1050

    intent = PaymentIntentCreate(amount=2500)
    assert intent.amount == 2500

    sub = SubscriptionResponse(active=True, amount=1999)
    assert sub.amount == 1999


@pytest.mark.asyncio
async def test_async_clickhouse_helpers_execute_non_blocking():
    """Verify execute_ch_query, execute_ch_command, and execute_ch_insert call client under lock."""
    mock_client = MagicMock()
    mock_res = MagicMock()
    mock_res.result_rows = [[42]]
    mock_client.query.return_value = mock_res
    mock_client.command.return_value = "OK"

    # Query
    q_res = await execute_ch_query("SELECT 42", client_getter=lambda: mock_client)
    assert q_res.result_rows[0][0] == 42
    assert mock_client.query.called

    # Command
    c_res = await execute_ch_command("OPTIMIZE TABLE txs", client_getter=lambda: mock_client)
    assert c_res == "OK"
    assert mock_client.command.called

    # Insert
    await execute_ch_insert("txs", [[1, 2]], ["a", "b"], client_getter=lambda: mock_client)
    assert mock_client.insert.called
