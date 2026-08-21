import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models import (
    Base,
    FederalReserveDistrict,
    Institution,
    MasterAccount,
    ACHTransaction,
    FedwireTransfer,
    FedNowTransfer,
)

def test_models_table_names():
    assert FederalReserveDistrict.__tablename__ == "fed_districts"
    assert Institution.__tablename__ == "institutions"
    assert MasterAccount.__tablename__ == "master_accounts"
    assert ACHTransaction.__tablename__ == "ach_transactions"
    assert FedwireTransfer.__tablename__ == "fedwire_transfers"
    assert FedNowTransfer.__tablename__ == "fednow_transfers"

def test_model_field_types():
    inst = Institution(
        routing_number="021000021",
        name="JPMorgan Chase Bank, N.A.",
        short_name="CHASE NY",
        district_id=2,
        office_code="O",
        servicing_frb_number="021000018",
        city="New York",
        state="NY",
        fedach_participant=True,
        fedwire_participant=True,
        fednow_participant=True,
        status="ACTIVE",
    )
    assert inst.routing_number == "021000021"
    assert inst.name == "JPMorgan Chase Bank, N.A."
    assert inst.district_id == 2

def test_master_account_defaults():
    ma = MasterAccount(
        account_number="FRB-021000021-01",
        routing_number="021000021",
    )
    assert ma.currency == "USD"
    assert ma.balance_cents == 1_000_000_000
    assert ma.daylight_overdraft_limit_cents == 500_000_000
    assert ma.status == "OPEN"
