import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from schemas import (
    ACHOriginateRequest,
    ACHBatchRequest,
    FedwireOriginateRequest,
    FedNowTransferRequest,
    RoutingLookupResponse,
    InstitutionOut,
    DistrictOut,
    MasterAccountResponse,
)

def test_ach_schema_defaults_and_fields():
    req = ACHOriginateRequest(
        originator_routing="123456780",
        originator_name="Karin Bank",
        originator_account="1001",
        receiver_routing="021000021",
        receiver_name="John Doe",
        receiver_account="987654321",
        amount=150.00,
    )
    assert req.amount == 150.00
    assert req.sec_code == "PPD"
    assert req.entry_class == "DEBIT"

def test_fedwire_schema():
    req = FedwireOriginateRequest(
        sender_routing="123456780",
        sender_name="Karin Bank",
        sender_account="1001",
        receiver_routing="021000021",
        receiver_name="Acme Corp",
        receiver_account="987654321",
        amount_cents=5000000,
    )
    assert req.business_function_code == "CTR"
    assert req.amount_cents == 5000000

def test_fednow_schema():
    req = FedNowTransferRequest(
        debtor_routing="123456780",
        debtor_name="Ikarin",
        debtor_account="1001",
        creditor_routing="111000012",
        creditor_name="Alex",
        creditor_account="2002",
        amount_cents=2500,
    )
    assert req.amount_cents == 2500
