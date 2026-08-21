import ast
import pathlib
import pytest
from pydantic import ValidationError

from schemas.transfers import WireTransferRequest, FedNowTransferRequest, ExternalACHTransferRequest

TRANSFERS_ROUTER = pathlib.Path("backend/routers/transfers.py")
VENDORS_ROUTER = pathlib.Path("backend/routers/vendors.py")
ADMIN_ROUTER = pathlib.Path("backend/routers/admin.py")

def _names_defined(source: str) -> set[str]:
    tree = ast.parse(source)
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }

def test_wire_transfer_schema_validation():
    # Valid
    wire = WireTransferRequest(
        account_id=1,
        amount=150000,
        receiver_routing="021000021",
        receiver_account="987654321",
        receiver_name="Acme Corp",
    )
    assert wire.amount == 150000
    assert wire.receiver_routing == "021000021"

    # Reject <= 0
    with pytest.raises(ValidationError):
        WireTransferRequest(
            account_id=1,
            amount=0,
            receiver_routing="021000021",
            receiver_account="987654321",
            receiver_name="Acme Corp",
        )

    # Reject bad routing length
    with pytest.raises(ValidationError):
        WireTransferRequest(
            account_id=1,
            amount=1000,
            receiver_routing="123",
            receiver_account="987654321",
            receiver_name="Acme Corp",
        )

def test_fednow_transfer_schema_validation():
    fednow = FedNowTransferRequest(
        account_id=1,
        amount=2500,
        creditor_routing="111000012",
        creditor_account="12345",
        creditor_name="Jane Doe",
    )
    assert fednow.amount == 2500

    with pytest.raises(ValidationError):
        FedNowTransferRequest(
            account_id=1,
            amount=-50,
            creditor_routing="111000012",
            creditor_account="12345",
            creditor_name="Jane Doe",
        )

def test_transfers_router_defines_fed_endpoints():
    source = TRANSFERS_ROUTER.read_text()
    names = _names_defined(source)
    assert "create_wire_transfer" in names, "create_wire_transfer not found in transfers router"
    assert "create_fednow_transfer" in names, "create_fednow_transfer not found in transfers router"
    assert "create_ach_transfer" in names, "create_ach_transfer not found in transfers router"

def test_vendors_router_defines_directory_endpoints():
    source = VENDORS_ROUTER.read_text()
    names = _names_defined(source)
    assert "lookup_routing_number" in names or "get_fed_directory_routing" in names, "routing lookup not found in vendors router"
    assert "get_fed_districts" in names or "get_districts" in names, "districts lookup not found in vendors router"

def test_admin_router_defines_fed_reserves():
    source = ADMIN_ROUTER.read_text()
    names = _names_defined(source)
    assert "get_fed_reserves" in names or "get_fed_master_account" in names, "fed reserves not found in admin router"
    assert "get_fed_daily_statement" in names, "fed daily statement not found in admin router"
