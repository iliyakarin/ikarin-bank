# High-Fidelity US Federal Reserve Mock Gateway Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a high-fidelity, multi-rail US Federal Reserve mock gateway simulating the E-Payments Routing Directory, FedACH, Fedwire RTGS, FedNow 24/7 instant payments, and Fed Master Account reserve accounting for Karin Bank.

**Architecture:** A modular Python / FastAPI service backed by PostgreSQL (`fed-gateway-db`) with dedicated domain modules for routing directory validation, ACH batches with NACHA return simulation, Fedwire RTGS with IMAD/OMAD tracking, FedNow ISO 20022 instant credit transfers, and master account ledger settlement.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy 2.0 (asyncio + asyncpg), Pydantic v2, PostgreSQL 16, pytest, pytest-asyncio, httpx.

**Spec:** `docs/superpowers/specs/2026-08-21-mock-fed-gateway-enhancements-design.md`

## Global Constraints
- Target directory: `mock-fed-gateway/`
- Authentication: Mandatory `X-API-KEY` header validation (`GATEWAY_API_KEY`) on payment and mutation endpoints.
- Database: Async SQLAlchemy with asyncpg on `fed-gateway-db:5432/fed_gateway_db`.
- Backward compatibility: `/banks` and `/fed/ach/originate` must maintain compatibility with existing backend callers.
- All monetary amounts handled in integer cents.
- DRY, modular router organization.

---

### Task 1: Routing Number & Checksum Utilities

**Files:**
- Create: `mock-fed-gateway/routing_utils.py`
- Test: `mock-fed-gateway/tests/test_routing_utils.py`

**Interfaces:**
- Produces:
  - `compute_routing_check_digit(digits: str) -> int`
  - `validate_routing_number(routing_number: str) -> dict`
  - `get_district_from_routing(routing_number: str) -> int`
  - `format_routing_number(digits: str) -> str`

- [ ] **Step 1: Write the failing test for routing utilities**

```python
# mock-fed-gateway/tests/test_routing_utils.py
import pytest
from routing_utils import (
    compute_routing_check_digit,
    validate_routing_number,
    get_district_from_routing,
    format_routing_number,
)

def test_compute_routing_check_digit_valid():
    # Chase NY (021000021) -> first 8 digits '02100002', check digit 1
    assert compute_routing_check_digit("02100002") == 1
    # BofA TX (111000012) -> first 8 digits '11100001', check digit 2
    assert compute_routing_check_digit("11100001") == 2
    # Karin Bank Node (123400010) -> first 8 digits '12340001', check digit 0
    assert compute_routing_check_digit("12340001") == 0

def test_validate_routing_number_success():
    res = validate_routing_number("021000021")
    assert res["valid"] is True
    assert res["district_id"] == 2
    assert len(res["errors"]) == 0

def test_validate_routing_number_invalid_checksum():
    res = validate_routing_number("021000029")
    assert res["valid"] is False
    assert "Invalid check digit" in res["errors"][0]

def test_validate_routing_number_invalid_length():
    res = validate_routing_number("123")
    assert res["valid"] is False
    assert "Expected 9 digits" in res["errors"][0]

def test_get_district_from_routing():
    assert get_district_from_routing("021000021") == 2
    assert get_district_from_routing("121000248") == 12
    assert get_district_from_routing("111000012") == 11
    assert get_district_from_routing("011103093") == 1

def test_format_routing_number():
    assert format_routing_number("021000021") == "0210-00021"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest mock-fed-gateway/tests/test_routing_utils.py -v`
Expected: FAIL (ModuleNotFoundError or routing_utils not found)

- [ ] **Step 3: Implement routing_utils.py**

```python
# mock-fed-gateway/routing_utils.py
import re
from typing import Dict, Any, List

ROUTING_REGEX = re.compile(r"^\d{9}$")
WEIGHTS = [3, 7, 1, 3, 7, 1, 3, 7]

def compute_routing_check_digit(digits: str) -> int:
    d8 = digits[:8] if len(digits) >= 8 else digits
    if len(d8) != 8 or not d8.isdigit():
        raise ValueError(f"Expected 8 numeric digits, got '{digits}'")
    
    total = sum(int(d8[i]) * WEIGHTS[i] for i in range(8))
    return (10 - (total % 10)) % 10

def get_district_from_routing(routing_number: str) -> int:
    digits = re.sub(r"\D", "", routing_number)
    if len(digits) < 2:
        return 0
    p = int(digits[:2])
    if 1 <= p <= 12:
        return p
    if 21 <= p <= 29:
        return 2   # NY
    if 30 <= p <= 32:
        return 3   # Philadelphia
    if 61 <= p <= 69:
        return 12  # San Francisco
    if 70 <= p <= 72:
        return 11  # Dallas
    if p == 80:
        return 8   # St. Louis / US Treasury
    if 90 <= p <= 92:
        return 12  # San Francisco
    return 12 if p >= 60 else (p % 12 or 12)

def validate_routing_number(routing_number: str) -> Dict[str, Any]:
    errors: List[str] = []
    if not isinstance(routing_number, str):
        return {"valid": False, "errors": ["Routing number must be a string"], "district_id": 0}
    
    cleaned = routing_number.strip()
    if not ROUTING_REGEX.match(cleaned):
        return {"valid": False, "errors": [f"Expected 9 digits, got '{cleaned}'"], "district_id": 0}
    
    if cleaned == "000000000":
        return {"valid": False, "errors": ["Routing number cannot be all zeros"], "district_id": 0}
    
    expected_check = compute_routing_check_digit(cleaned[:8])
    actual_check = int(cleaned[8])
    if actual_check != expected_check:
        return {
            "valid": False,
            "errors": [f"Invalid check digit: expected {expected_check}, got {actual_check}"],
            "district_id": get_district_from_routing(cleaned),
        }
    
    district_id = get_district_from_routing(cleaned)
    return {
        "valid": True,
        "errors": [],
        "district_id": district_id,
        "check_digit": actual_check,
    }

def format_routing_number(digits: str) -> str:
    clean = re.sub(r"\D", "", digits)
    if len(clean) == 9:
        return f"{clean[:4]}-{clean[4:]}"
    return digits
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest mock-fed-gateway/tests/test_routing_utils.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add mock-fed-gateway/routing_utils.py mock-fed-gateway/tests/test_routing_utils.py
git commit -m "feat(fed-gateway): add ABA Mod-10 routing number validation and district parsing"
```

---

### Task 2: Database Models & Engine Configuration

**Files:**
- Modify: `mock-fed-gateway/models.py`
- Create: `mock-fed-gateway/database.py`
- Test: `mock-fed-gateway/tests/test_models.py`

**Interfaces:**
- Produces:
  - `Base`, `FederalReserveDistrict`, `Institution`, `MasterAccount`, `ACHTransaction`, `FedwireTransfer`, `FedNowTransfer`
  - `get_db()`, `engine`, `AsyncSessionLocal`, `init_db()`

- [ ] **Step 1: Write failing test for database models and schema initialization**

```python
# mock-fed-gateway/tests/test_models.py
import pytest
from sqlalchemy import select
from models import Base, FederalReserveDistrict, Institution, MasterAccount, ACHTransaction, FedwireTransfer, FedNowTransfer

def test_models_structure():
    assert FederalReserveDistrict.__tablename__ == "fed_districts"
    assert Institution.__tablename__ == "institutions"
    assert MasterAccount.__tablename__ == "master_accounts"
    assert ACHTransaction.__tablename__ == "ach_transactions"
    assert FedwireTransfer.__tablename__ == "fedwire_transfers"
    assert FedNowTransfer.__tablename__ == "fednow_transfers"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest mock-fed-gateway/tests/test_models.py -v`
Expected: FAIL (missing model attributes)

- [ ] **Step 3: Implement database.py and updated models.py**

```python
# mock-fed-gateway/database.py
import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from models import Base

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    user = os.getenv("FED_GATEWAY_DB_USER", "admin")
    password = os.getenv("FED_GATEWAY_DB_PASSWORD", "admin123")
    host = os.getenv("FED_GATEWAY_DB_HOST", "fed-gateway-db")
    db_name = os.getenv("FED_GATEWAY_DB_NAME", "fed_gateway_db")
    DATABASE_URL = f"postgresql+asyncpg://{user}:{password}@{host}:5432/{db_name}"

engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

```python
# mock-fed-gateway/models.py
from datetime import datetime, date, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy import String, Integer, BigInteger, Boolean, Date, DateTime, ForeignKey, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import AsyncAttrs

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class Base(AsyncAttrs, DeclarativeBase):
    pass

class FederalReserveDistrict(Base):
    __tablename__ = "fed_districts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(2), unique=True, nullable=False)  # "01" - "12"
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    district_letter: Mapped[str] = mapped_column(String(1), nullable=False)    # "A" - "L"
    head_office_city: Mapped[str] = mapped_column(String(50), nullable=False)
    head_office_state: Mapped[str] = mapped_column(String(2), nullable=False)
    routing_prefix_ranges: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)

    institutions: Mapped[List["Institution"]] = relationship("Institution", back_populates="district")

class Institution(Base):
    __tablename__ = "institutions"

    routing_number: Mapped[str] = mapped_column(String(9), primary_key=True, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    short_name: Mapped[str] = mapped_column(String(50), nullable=False)
    district_id: Mapped[int] = mapped_column(Integer, ForeignKey("fed_districts.id"), nullable=False)
    office_code: Mapped[str] = mapped_column(String(1), default="O")  # O = Main, B = Branch
    servicing_frb_number: Mapped[str] = mapped_column(String(9), nullable=False)
    address: Mapped[str] = mapped_column(String(255), default="")
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(2), nullable=False)
    zip_code: Mapped[str] = mapped_column(String(10), default="")
    phone: Mapped[str] = mapped_column(String(20), default="")
    fedach_participant: Mapped[bool] = mapped_column(Boolean, default=True)
    fedwire_participant: Mapped[bool] = mapped_column(Boolean, default=True)
    fednow_participant: Mapped[bool] = mapped_column(Boolean, default=True)
    settlement_only: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")  # ACTIVE, SUSPENDED, IN_RECEIVERSHIP
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    district: Mapped["FederalReserveDistrict"] = relationship("FederalReserveDistrict", back_populates="institutions")
    master_account: Mapped[Optional["MasterAccount"]] = relationship("MasterAccount", back_populates="institution", uselist=False)

class MasterAccount(Base):
    __tablename__ = "master_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)
    routing_number: Mapped[str] = mapped_column(String(9), ForeignKey("institutions.routing_number"), unique=True, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    balance_cents: Mapped[int] = mapped_column(BigInteger, default=1_000_000_000)  # $10,000,000.00 default
    daylight_overdraft_limit_cents: Mapped[int] = mapped_column(BigInteger, default=500_000_000)  # $5M
    status: Mapped[str] = mapped_column(String(20), default="OPEN")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    institution: Mapped["Institution"] = relationship("Institution", back_populates="master_account")

class ACHTransaction(Base):
    __tablename__ = "ach_transactions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    batch_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    sec_code: Mapped[str] = mapped_column(String(3), default="PPD")  # PPD, CCD, WEB, TEL, CIE
    originator_routing: Mapped[str] = mapped_column(String(9), nullable=False)
    originator_name: Mapped[str] = mapped_column(String(100), nullable=False)
    originator_account: Mapped[str] = mapped_column(String(50), nullable=False)
    receiver_routing: Mapped[str] = mapped_column(String(9), nullable=False)
    receiver_name: Mapped[str] = mapped_column(String(100), nullable=False)
    receiver_account: Mapped[str] = mapped_column(String(50), nullable=False)
    amount_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    entry_class: Mapped[str] = mapped_column(String(10), default="DEBIT")  # DEBIT / CREDIT
    payment_description: Mapped[str] = mapped_column(String(100), default="")
    status: Mapped[str] = mapped_column(String(20), default="SETTLED")  # SETTLED, RETURNED, PENDING
    return_code: Mapped[Optional[str]] = mapped_column(String(3), nullable=True)
    return_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    settlement_date: Mapped[date] = mapped_column(Date, default=lambda: datetime.now(timezone.utc).date())
    trace_number: Mapped[str] = mapped_column(String(15), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

class FedwireTransfer(Base):
    __tablename__ = "fedwire_transfers"

    imad: Mapped[str] = mapped_column(String(24), primary_key=True)
    omad: Mapped[str] = mapped_column(String(24), unique=True, nullable=False)
    business_function_code: Mapped[str] = mapped_column(String(3), default="CTR")  # CTR, BTR, DEP, DRC
    sender_routing: Mapped[str] = mapped_column(String(9), nullable=False)
    sender_name: Mapped[str] = mapped_column(String(100), nullable=False)
    sender_account: Mapped[str] = mapped_column(String(50), nullable=False)
    receiver_routing: Mapped[str] = mapped_column(String(9), nullable=False)
    receiver_name: Mapped[str] = mapped_column(String(100), nullable=False)
    receiver_account: Mapped[str] = mapped_column(String(50), nullable=False)
    amount_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    charge_details: Mapped[str] = mapped_column(String(3), default="OUR")  # OUR, BEN, SHA
    payment_reference: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="SETTLED")  # SETTLED, REJECTED, PENDING
    rejection_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    settlement_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

class FedNowTransfer(Base):
    __tablename__ = "fednow_transfers"

    end_to_end_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    instruction_id: Mapped[str] = mapped_column(String(36), nullable=False)
    message_type: Mapped[str] = mapped_column(String(30), default="CREDIT_TRANSFER")  # CREDIT_TRANSFER, RFP
    debtor_routing: Mapped[str] = mapped_column(String(9), nullable=False)
    debtor_name: Mapped[str] = mapped_column(String(100), nullable=False)
    debtor_account: Mapped[str] = mapped_column(String(50), nullable=False)
    creditor_routing: Mapped[str] = mapped_column(String(9), nullable=False)
    creditor_name: Mapped[str] = mapped_column(String(100), nullable=False)
    creditor_account: Mapped[str] = mapped_column(String(50), nullable=False)
    amount_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[str] = mapped_column(String(10), default="ACCP")  # ACCP, RJCT, PEND
    status_reason_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    status_reason_description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest mock-fed-gateway/tests/test_models.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add mock-fed-gateway/models.py mock-fed-gateway/database.py mock-fed-gateway/tests/test_models.py
git commit -m "feat(fed-gateway): add comprehensive SQLAlchemy models for Fed Directory, ACH, Fedwire, FedNow, and Master Accounts"
```

---

### Task 3: Authentic Federal Reserve Districts & Institution Seed Dataset

**Files:**
- Create: `mock-fed-gateway/seed_data.py`
- Test: `mock-fed-gateway/tests/test_seed_data.py`

**Interfaces:**
- Produces:
  - `FED_DISTRICTS_DATA: List[Dict[str, Any]]`
  - `INSTITUTIONS_DATA: List[Dict[str, Any]]`
  - `seed_all_data(session: AsyncSession) -> Dict[str, int]`

- [ ] **Step 1: Write failing test verifying seed dataset authenticity and valid checksums**

```python
# mock-fed-gateway/tests/test_seed_data.py
import pytest
from seed_data import FED_DISTRICTS_DATA, INSTITUTIONS_DATA
from routing_utils import validate_routing_number

def test_districts_data_count_and_keys():
    assert len(FED_DISTRICTS_DATA) == 12
    codes = [d["code"] for d in FED_DISTRICTS_DATA]
    assert sorted(codes) == [f"{i:02d}" for i in range(1, 13)]

def test_all_institutions_have_valid_routing_checksums():
    assert len(INSTITUTIONS_DATA) >= 35
    for inst in INSTITUTIONS_DATA:
        res = validate_routing_number(inst["routing_number"])
        assert res["valid"] is True, f"Institution {inst['name']} has invalid RTN: {inst['routing_number']} error: {res['errors']}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest mock-fed-gateway/tests/test_seed_data.py -v`
Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 3: Implement seed_data.py with authentic districts, top US banks, and Karin Bank node**

```python
# mock-fed-gateway/seed_data.py
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from models import FederalReserveDistrict, Institution, MasterAccount

FED_DISTRICTS_DATA: List[Dict[str, Any]] = [
    {"id": 1, "code": "01", "name": "Federal Reserve Bank of Boston", "district_letter": "A", "head_office_city": "Boston", "head_office_state": "MA", "routing_prefix_ranges": ["01", "21"]},
    {"id": 2, "code": "02", "name": "Federal Reserve Bank of New York", "district_letter": "B", "head_office_city": "New York", "head_office_state": "NY", "routing_prefix_ranges": ["02", "22"]},
    {"id": 3, "code": "03", "name": "Federal Reserve Bank of Philadelphia", "district_letter": "C", "head_office_city": "Philadelphia", "head_office_state": "PA", "routing_prefix_ranges": ["03", "23", "30", "31", "32"]},
    {"id": 4, "code": "04", "name": "Federal Reserve Bank of Cleveland", "district_letter": "D", "head_office_city": "Cleveland", "head_office_state": "OH", "routing_prefix_ranges": ["04", "24"]},
    {"id": 5, "code": "05", "name": "Federal Reserve Bank of Richmond", "district_letter": "E", "head_office_city": "Richmond", "head_office_state": "VA", "routing_prefix_ranges": ["05", "25"]},
    {"id": 6, "code": "06", "name": "Federal Reserve Bank of Atlanta", "district_letter": "F", "head_office_city": "Atlanta", "head_office_state": "GA", "routing_prefix_ranges": ["06", "26"]},
    {"id": 7, "code": "07", "name": "Federal Reserve Bank of Chicago", "district_letter": "G", "head_office_city": "Chicago", "head_office_state": "IL", "routing_prefix_ranges": ["07", "27"]},
    {"id": 8, "code": "08", "name": "Federal Reserve Bank of St. Louis", "district_letter": "H", "head_office_city": "St. Louis", "head_office_state": "MO", "routing_prefix_ranges": ["08", "28", "80"]},
    {"id": 9, "code": "09", "name": "Federal Reserve Bank of Minneapolis", "district_letter": "I", "head_office_city": "Minneapolis", "head_office_state": "MN", "routing_prefix_ranges": ["09", "29"]},
    {"id": 10, "code": "10", "name": "Federal Reserve Bank of Kansas City", "district_letter": "J", "head_office_city": "Kansas City", "head_office_state": "MO", "routing_prefix_ranges": ["10", "30"]},
    {"id": 11, "code": "11", "name": "Federal Reserve Bank of Dallas", "district_letter": "K", "head_office_city": "Dallas", "head_office_state": "TX", "routing_prefix_ranges": ["11", "31", "70", "71", "72"]},
    {"id": 12, "code": "12", "name": "Federal Reserve Bank of San Francisco", "district_letter": "L", "head_office_city": "San Francisco", "head_office_state": "CA", "routing_prefix_ranges": ["12", "32", "61", "62", "63", "64", "65", "66", "67", "68", "69", "90", "91", "92"]},
]

INSTITUTIONS_DATA: List[Dict[str, Any]] = [
    # Karin Bank Node
    {"routing_number": "123400010", "name": "Karin Bank, N.A.", "short_name": "KARIN SFO", "district_id": 12, "office_code": "O", "servicing_frb_number": "121000019", "address": "100 California St", "city": "San Francisco", "state": "CA", "zip_code": "94111", "phone": "415-555-0100", "fedach_participant": True, "fedwire_participant": True, "fednow_participant": True, "status": "ACTIVE"},
    {"routing_number": "123456780", "name": "Karin Bank Austin Operations", "short_name": "KARIN ATX", "district_id": 11, "office_code": "B", "servicing_frb_number": "111000012", "address": "500 Congress Ave", "city": "Austin", "state": "TX", "zip_code": "78701", "phone": "512-555-0140", "fedach_participant": True, "fedwire_participant": True, "fednow_participant": True, "status": "ACTIVE"},

    # Top US Banks
    {"routing_number": "021000021", "name": "JPMorgan Chase Bank, N.A.", "short_name": "CHASE NY", "district_id": 2, "office_code": "O", "servicing_frb_number": "021000018", "address": "270 Park Ave", "city": "New York", "state": "NY", "zip_code": "10017", "phone": "212-270-6000", "fedach_participant": True, "fedwire_participant": True, "fednow_participant": True, "status": "ACTIVE"},
    {"routing_number": "122241255", "name": "JPMorgan Chase Bank (California)", "short_name": "CHASE LA", "district_id": 12, "office_code": "B", "servicing_frb_number": "121000019", "address": "1999 Avenue of the Stars", "city": "Los Angeles", "state": "CA", "zip_code": "90067", "phone": "310-860-7000", "fedach_participant": True, "fedwire_participant": True, "fednow_participant": True, "status": "ACTIVE"},
    {"routing_number": "071000013", "name": "JPMorgan Chase Bank (Chicago)", "short_name": "CHASE CHI", "district_id": 7, "office_code": "B", "servicing_frb_number": "071000301", "address": "10 S Dearborn St", "city": "Chicago", "state": "IL", "zip_code": "60603", "phone": "312-732-4000", "fedach_participant": True, "fedwire_participant": True, "fednow_participant": True, "status": "ACTIVE"},

    {"routing_number": "111000012", "name": "Bank of America, N.A. (Texas)", "short_name": "BOA DAL", "district_id": 11, "office_code": "B", "servicing_frb_number": "111000012", "address": "901 Main St", "city": "Dallas", "state": "TX", "zip_code": "75202", "phone": "214-209-1000", "fedach_participant": True, "fedwire_participant": True, "fednow_participant": True, "status": "ACTIVE"},
    {"routing_number": "121000358", "name": "Bank of America, N.A. (California)", "short_name": "BOA SFO", "district_id": 12, "office_code": "B", "servicing_frb_number": "121000019", "address": "333 S Hope St", "city": "Los Angeles", "state": "CA", "zip_code": "90071", "phone": "213-345-6789", "fedach_participant": True, "fedwire_participant": True, "fednow_participant": True, "status": "ACTIVE"},
    {"routing_number": "053000196", "name": "Bank of America, N.A. (HQ)", "short_name": "BOA NC", "district_id": 5, "office_code": "O", "servicing_frb_number": "053000206", "address": "100 N Tryon St", "city": "Charlotte", "state": "NC", "zip_code": "28255", "phone": "800-432-1000", "fedach_participant": True, "fedwire_participant": True, "fednow_participant": True, "status": "ACTIVE"},

    {"routing_number": "121000248", "name": "Wells Fargo Bank, N.A.", "short_name": "WELLS SFO", "district_id": 12, "office_code": "O", "servicing_frb_number": "121000019", "address": "420 Montgomery St", "city": "San Francisco", "state": "CA", "zip_code": "94104", "phone": "800-869-3557", "fedach_participant": True, "fedwire_participant": True, "fednow_participant": True, "status": "ACTIVE"},
    {"routing_number": "091000019", "name": "Wells Fargo Bank (Northwest)", "short_name": "WELLS MSP", "district_id": 9, "office_code": "B", "servicing_frb_number": "091000080", "address": "90 S 7th St", "city": "Minneapolis", "state": "MN", "zip_code": "55402", "phone": "612-667-1234", "fedach_participant": True, "fedwire_participant": True, "fednow_participant": True, "status": "ACTIVE"},
    {"routing_number": "102000076", "name": "Wells Fargo Bank (Colorado)", "short_name": "WELLS DEN", "district_id": 10, "office_code": "B", "servicing_frb_number": "102000199", "address": "1700 Lincoln St", "city": "Denver", "state": "CO", "zip_code": "80203", "phone": "303-863-6000", "fedach_participant": True, "fedwire_participant": True, "fednow_participant": True, "status": "ACTIVE"},

    {"routing_number": "021000089", "name": "Citibank, N.A.", "short_name": "CITI NY", "district_id": 2, "office_code": "O", "servicing_frb_number": "021000018", "address": "388 Greenwich St", "city": "New York", "state": "NY", "zip_code": "10013", "phone": "212-559-1000", "fedach_participant": True, "fedwire_participant": True, "fednow_participant": True, "status": "ACTIVE"},
    {"routing_number": "321171184", "name": "Citibank, N.A. (South Dakota)", "short_name": "CITI SD", "district_id": 9, "office_code": "B", "servicing_frb_number": "091000080", "address": "701 E 60th St N", "city": "Sioux Falls", "state": "SD", "zip_code": "57104", "phone": "605-331-2000", "fedach_participant": True, "fedwire_participant": True, "fednow_participant": True, "status": "ACTIVE"},

    {"routing_number": "091000022", "name": "U.S. Bank National Association", "short_name": "USBANK MSP", "district_id": 9, "office_code": "O", "servicing_frb_number": "091000080", "address": "800 Nicollet Mall", "city": "Minneapolis", "state": "MN", "zip_code": "55402", "phone": "800-872-2657", "fedach_participant": True, "fedwire_participant": True, "fednow_participant": True, "status": "ACTIVE"},
    {"routing_number": "123000848", "name": "U.S. Bank (Oregon)", "short_name": "USBANK PDX", "district_id": 12, "office_code": "B", "servicing_frb_number": "121000019", "address": "111 SW 5th Ave", "city": "Portland", "state": "OR", "zip_code": "97204", "phone": "503-275-6111", "fedach_participant": True, "fedwire_participant": True, "fednow_participant": True, "status": "ACTIVE"},

    {"routing_number": "043000096", "name": "PNC Bank, National Association", "short_name": "PNC PIT", "district_id": 4, "office_code": "O", "servicing_frb_number": "043000300", "address": "300 Fifth Ave", "city": "Pittsburgh", "state": "PA", "zip_code": "15222", "phone": "888-762-2265", "fedach_participant": True, "fedwire_participant": True, "fednow_participant": True, "status": "ACTIVE"},
    {"routing_number": "071921891", "name": "PNC Bank (Midwest)", "short_name": "PNC CHI", "district_id": 7, "office_code": "B", "servicing_frb_number": "071000301", "address": "1 N Franklin St", "city": "Chicago", "state": "IL", "zip_code": "60606", "phone": "312-384-4000", "fedach_participant": True, "fedwire_participant": True, "fednow_participant": True, "status": "ACTIVE"},

    {"routing_number": "061000104", "name": "Truist Bank", "short_name": "TRUIST ATL", "district_id": 6, "office_code": "O", "servicing_frb_number": "061000146", "address": "214 N Tryon St", "city": "Charlotte", "state": "NC", "zip_code": "28202", "phone": "844-487-8478", "fedach_participant": True, "fedwire_participant": True, "fednow_participant": True, "status": "ACTIVE"},
    {"routing_number": "026002561", "name": "Goldman Sachs Bank USA", "short_name": "GS NY", "district_id": 2, "office_code": "O", "servicing_frb_number": "021000018", "address": "200 West St", "city": "New York", "state": "NY", "zip_code": "10282", "phone": "212-902-1000", "fedach_participant": True, "fedwire_participant": True, "fednow_participant": True, "status": "ACTIVE"},
    {"routing_number": "026013576", "name": "Morgan Stanley Private Bank, N.A.", "short_name": "MS NY", "district_id": 2, "office_code": "O", "servicing_frb_number": "021000018", "address": "1585 Broadway", "city": "New York", "state": "NY", "zip_code": "10036", "phone": "212-761-4000", "fedach_participant": True, "fedwire_participant": True, "fednow_participant": True, "status": "ACTIVE"},

    {"routing_number": "051405515", "name": "Capital One, N.A.", "short_name": "CAPONE VA", "district_id": 5, "office_code": "O", "servicing_frb_number": "053000206", "address": "1680 Capital One Dr", "city": "McLean", "state": "VA", "zip_code": "22102", "phone": "877-383-4802", "fedach_participant": True, "fedwire_participant": True, "fednow_participant": True, "status": "ACTIVE"},
    {"routing_number": "011103093", "name": "TD Bank, N.A.", "short_name": "TD PORT", "district_id": 1, "office_code": "O", "servicing_frb_number": "011000015", "address": "One Portland Square", "city": "Portland", "state": "ME", "zip_code": "04101", "phone": "888-751-9000", "fedach_participant": True, "fedwire_participant": True, "fednow_participant": True, "status": "ACTIVE"},
    {"routing_number": "021000018", "name": "The Bank of New York Mellon", "short_name": "BNY MELLON", "district_id": 2, "office_code": "O", "servicing_frb_number": "021000018", "address": "240 Greenwich St", "city": "New York", "state": "NY", "zip_code": "10286", "phone": "212-495-1784", "fedach_participant": True, "fedwire_participant": True, "fednow_participant": True, "status": "ACTIVE"},
    {"routing_number": "011000028", "name": "State Street Bank and Trust Company", "short_name": "STATE STREET", "district_id": 1, "office_code": "O", "servicing_frb_number": "011000015", "address": "1 Lincoln St", "city": "Boston", "state": "MA", "zip_code": "02111", "phone": "617-786-3000", "fedach_participant": True, "fedwire_participant": True, "fednow_participant": True, "status": "ACTIVE"},

    {"routing_number": "121202211", "name": "Charles Schwab Bank, SSB", "short_name": "SCHWAB TX", "district_id": 11, "office_code": "O", "servicing_frb_number": "111000012", "address": "3000 Schwab Way", "city": "Westlake", "state": "TX", "zip_code": "76262", "phone": "888-403-9000", "fedach_participant": True, "fedwire_participant": True, "fednow_participant": True, "status": "ACTIVE"},
    {"routing_number": "101000695", "name": "UMB Bank, N.A. (Fidelity)", "short_name": "UMB FIDELITY", "district_id": 10, "office_code": "O", "servicing_frb_number": "102000199", "address": "1010 Grand Blvd", "city": "Kansas City", "state": "MO", "zip_code": "64106", "phone": "816-860-7000", "fedach_participant": True, "fedwire_participant": True, "fednow_participant": True, "status": "ACTIVE"},

    # Credit Unions & Digital
    {"routing_number": "256074974", "name": "Navy Federal Credit Union", "short_name": "NAVY FED", "district_id": 5, "office_code": "O", "servicing_frb_number": "053000206", "address": "820 Follin Ln", "city": "Vienna", "state": "VA", "zip_code": "22180", "phone": "888-842-6328", "fedach_participant": True, "fedwire_participant": True, "fednow_participant": True, "status": "ACTIVE"},
    {"routing_number": "253177093", "name": "State Employees' Credit Union", "short_name": "SECU NC", "district_id": 5, "office_code": "O", "servicing_frb_number": "053000206", "address": "119 N Salisbury St", "city": "Raleigh", "state": "NC", "zip_code": "27603", "phone": "888-732-8562", "fedach_participant": True, "fedwire_participant": True, "fednow_participant": False, "status": "ACTIVE"},
    {"routing_number": "124003116", "name": "Ally Bank", "short_name": "ALLY UT", "district_id": 12, "office_code": "O", "servicing_frb_number": "121000019", "address": "6985 Union Park Center", "city": "Midvale", "state": "UT", "zip_code": "84047", "phone": "877-247-2559", "fedach_participant": True, "fedwire_participant": True, "fednow_participant": True, "status": "ACTIVE"},
    {"routing_number": "121140399", "name": "Silicon Valley Bank (First-Citizens)", "short_name": "SVB FCB", "district_id": 12, "office_code": "B", "servicing_frb_number": "121000019", "address": "3003 Tasman Dr", "city": "Santa Clara", "state": "CA", "zip_code": "95054", "phone": "800-774-7390", "fedach_participant": True, "fedwire_participant": True, "fednow_participant": True, "status": "ACTIVE"},
    {"routing_number": "022000046", "name": "M&T Bank", "short_name": "M&T BUF", "district_id": 2, "office_code": "O", "servicing_frb_number": "021000018", "address": "One M&T Plaza", "city": "Buffalo", "state": "NY", "zip_code": "14203", "phone": "800-724-2440", "fedach_participant": True, "fedwire_participant": True, "fednow_participant": True, "status": "ACTIVE"},
    {"routing_number": "042000314", "name": "Fifth Third Bank, National Association", "short_name": "53 CIN", "district_id": 4, "office_code": "O", "servicing_frb_number": "043000300", "address": "38 Fountain Sq Plaza", "city": "Cincinnati", "state": "OH", "zip_code": "45263", "phone": "800-972-3030", "fedach_participant": True, "fedwire_participant": True, "fednow_participant": True, "status": "ACTIVE"},
    {"routing_number": "041001039", "name": "KeyBank National Association", "short_name": "KEYBANK CLE", "district_id": 4, "office_code": "O", "servicing_frb_number": "043000300", "address": "127 Public Sq", "city": "Cleveland", "state": "OH", "zip_code": "44114", "phone": "800-539-2968", "fedach_participant": True, "fedwire_participant": True, "fednow_participant": True, "status": "ACTIVE"},
    {"routing_number": "011500120", "name": "Citizens Bank, N.A.", "short_name": "CITIZENS RI", "district_id": 1, "office_code": "O", "servicing_frb_number": "011000015", "address": "One Citizens Plaza", "city": "Providence", "state": "RI", "zip_code": "02903", "phone": "800-922-9999", "fedach_participant": True, "fedwire_participant": True, "fednow_participant": True, "status": "ACTIVE"},
    {"routing_number": "062000019", "name": "Regions Bank", "short_name": "REGIONS BHM", "district_id": 6, "office_code": "O", "servicing_frb_number": "061000146", "address": "1900 5th Ave N", "city": "Birmingham", "state": "AL", "zip_code": "35203", "phone": "800-734-4667", "fedach_participant": True, "fedwire_participant": True, "fednow_participant": True, "status": "ACTIVE"},
    {"routing_number": "044000024", "name": "The Huntington National Bank", "short_name": "HUNTINGTON OH", "district_id": 4, "office_code": "O", "servicing_frb_number": "043000300", "address": "41 S High St", "city": "Columbus", "state": "OH", "zip_code": "43215", "phone": "800-480-2265", "fedach_participant": True, "fedwire_participant": True, "fednow_participant": True, "status": "ACTIVE"},
    {"routing_number": "071000288", "name": "BMO Bank National Association", "short_name": "BMO CHI", "district_id": 7, "office_code": "O", "servicing_frb_number": "071000301", "address": "320 S Canal St", "city": "Chicago", "state": "IL", "zip_code": "60606", "phone": "888-340-2265", "fedach_participant": True, "fedwire_participant": True, "fednow_participant": True, "status": "ACTIVE"},
]

async def seed_all_data(session: AsyncSession) -> Dict[str, int]:
    # 1. Seed Districts if missing
    res = await session.execute(select(FederalReserveDistrict))
    existing_districts = {d.id: d for d in res.scalars().all()}
    districts_added = 0
    for d in FED_DISTRICTS_DATA:
        if d["id"] not in existing_districts:
            session.add(FederalReserveDistrict(**d))
            districts_added += 1
    await session.flush()

    # 2. Seed Institutions
    res = await session.execute(select(Institution))
    existing_inst = {inst.routing_number: inst for inst in res.scalars().all()}
    institutions_added = 0
    for inst in INSTITUTIONS_DATA:
        if inst["routing_number"] not in existing_inst:
            session.add(Institution(**inst))
            institutions_added += 1
    await session.flush()

    # 3. Seed Master Accounts for all active institutions
    res = await session.execute(select(Institution))
    all_insts = res.scalars().all()
    res = await session.execute(select(MasterAccount))
    existing_accounts = {ma.routing_number: ma for ma in res.scalars().all()}
    accounts_added = 0
    for inst in all_insts:
        if inst.routing_number not in existing_accounts:
            acct_num = f"FRB-{inst.routing_number}-01"
            session.add(MasterAccount(
                account_number=acct_num,
                routing_number=inst.routing_number,
                balance_cents=1_000_000_000,  # $10M reserve
                daylight_overdraft_limit_cents=500_000_000,  # $5M limit
                status="OPEN",
            ))
            accounts_added += 1
    
    await session.commit()
    return {
        "districts_added": districts_added,
        "institutions_added": institutions_added,
        "accounts_added": accounts_added,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest mock-fed-gateway/tests/test_seed_data.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add mock-fed-gateway/seed_data.py mock-fed-gateway/tests/test_seed_data.py
git commit -m "feat(fed-gateway): add authentic seed data for 12 Fed districts, 35+ top US banks, and prefunded master accounts"
```

---

### Task 4: Pydantic Schemas for Multi-Rail Fed APIs

**Files:**
- Modify: `mock-fed-gateway/schemas.py`
- Test: `mock-fed-gateway/tests/test_schemas.py`

**Interfaces:**
- Produces:
  - `InstitutionOut`, `DistrictOut`, `DirectorySearchResponse`, `RoutingLookupResponse`
  - `ACHOriginateRequest`, `ACHBatchRequest`, `ACHTransactionResponse`, `ACHBatchResponse`
  - `FedwireOriginateRequest`, `FedwireTransferResponse`
  - `FedNowTransferRequest`, `FedNowRFPRequest`, `FedNowTransferResponse`
  - `MasterAccountResponse`, `MasterAccountAdjustRequest`, `DailyStatementResponse`

- [ ] **Step 1: Write failing test for schemas**

```python
# mock-fed-gateway/tests/test_schemas.py
import pytest
from schemas import (
    ACHOriginateRequest,
    FedwireOriginateRequest,
    FedNowTransferRequest,
    RoutingLookupResponse,
)

def test_ach_schema_cents_or_dollars():
    req = ACHOriginateRequest(
        originator_routing="123400010",
        originator_name="Karin Bank",
        originator_account="1001",
        receiver_routing="021000021",
        receiver_name="John Doe",
        receiver_account="987654321",
        amount=150.00,
    )
    assert req.amount == 150.00
    assert req.sec_code == "PPD"

def test_fedwire_schema():
    req = FedwireOriginateRequest(
        sender_routing="123400010",
        sender_name="Karin Bank",
        sender_account="1001",
        receiver_routing="021000021",
        receiver_name="Acme Corp",
        receiver_account="987654321",
        amount_cents=5000000,
    )
    assert req.business_function_code == "CTR"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest mock-fed-gateway/tests/test_schemas.py -v`
Expected: FAIL

- [ ] **Step 3: Implement comprehensive schemas.py**

```python
# mock-fed-gateway/schemas.py
from datetime import datetime, date
from typing import Optional, List, Union, Dict, Any
from pydantic import BaseModel, Field

# --- Directory & Districts ---
class DistrictOut(BaseModel):
    id: int
    code: str
    name: str
    district_letter: str
    head_office_city: str
    head_office_state: str
    routing_prefix_ranges: Optional[List[str]] = None

class InstitutionOut(BaseModel):
    routing_number: str
    name: str
    short_name: str
    district_id: int
    office_code: str
    servicing_frb_number: str
    city: str
    state: str
    zip_code: str
    phone: str
    fedach_participant: bool
    fedwire_participant: bool
    fednow_participant: bool
    status: str

class DirectorySearchResponse(BaseModel):
    total: int
    institutions: List[InstitutionOut]

class RoutingLookupResponse(BaseModel):
    valid: bool
    routing_number: str
    formatted: str
    institution: Optional[InstitutionOut] = None
    district: Optional[DistrictOut] = None
    errors: List[str] = []

class BankSimple(BaseModel):
    name: str
    routing_number: str

class BankListResponse(BaseModel):
    banks: List[BankSimple]

# --- FedACH ---
class ACHOriginateRequest(BaseModel):
    originator_routing: Optional[str] = Field(None, min_length=9, max_length=9)
    originator_name: Optional[str] = "Originating Institution"
    originator_account: Optional[str] = "100001"
    receiver_routing: Optional[str] = Field(None, min_length=9, max_length=9)
    routing_number: Optional[str] = Field(None, min_length=9, max_length=9) # For backward compatibility
    receiver_name: Optional[str] = "Receiver Customer"
    receiver_account: Optional[str] = None
    account_number: Optional[str] = None # For backward compatibility
    amount: Union[int, float] = Field(..., gt=0, description="Amount in cents (int) or dollars (float)")
    sec_code: str = "PPD"
    entry_class: str = "DEBIT"
    payment_description: Optional[str] = "ACH Payment"
    type: str = "ACH"

class ACHTransactionResponse(BaseModel):
    id: str
    trace_number: str
    sec_code: str
    originator_routing: str
    receiver_routing: str
    amount_cents: int
    entry_class: str
    status: str # SETTLED, RETURNED, PENDING
    return_code: Optional[str] = None
    return_reason: Optional[str] = None
    settlement_date: date
    message: Optional[str] = None

class ACHBatchEntry(BaseModel):
    receiver_routing: str
    receiver_name: str
    receiver_account: str
    amount: Union[int, float]
    sec_code: str = "PPD"
    entry_class: str = "DEBIT"
    payment_description: Optional[str] = ""

class ACHBatchRequest(BaseModel):
    originator_routing: str
    originator_name: str
    originator_account: str
    entries: List[ACHBatchEntry]

class ACHBatchResponse(BaseModel):
    batch_id: str
    total_entries: int
    settled_count: int
    returned_count: int
    total_debits_cents: int
    total_credits_cents: int
    transactions: List[ACHTransactionResponse]

# --- Fedwire (RTGS) ---
class FedwireOriginateRequest(BaseModel):
    sender_routing: str = Field(..., min_length=9, max_length=9)
    sender_name: str
    sender_account: str
    receiver_routing: str = Field(..., min_length=9, max_length=9)
    receiver_name: str
    receiver_account: str
    amount_cents: int = Field(..., gt=0)
    business_function_code: str = "CTR" # CTR, BTR, DEP, DRC
    charge_details: str = "OUR"
    payment_reference: Optional[str] = None

class FedwireTransferResponse(BaseModel):
    imad: str
    omad: str
    business_function_code: str
    sender_routing: str
    receiver_routing: str
    amount_cents: int
    status: str # SETTLED, REJECTED, PENDING
    rejection_reason: Optional[str] = None
    settlement_timestamp: datetime

# --- FedNow (Instant Payments) ---
class FedNowTransferRequest(BaseModel):
    end_to_end_id: Optional[str] = None
    instruction_id: Optional[str] = None
    debtor_routing: str = Field(..., min_length=9, max_length=9)
    debtor_name: str
    debtor_account: str
    creditor_routing: str = Field(..., min_length=9, max_length=9)
    creditor_name: str
    creditor_account: str
    amount_cents: int = Field(..., gt=0)
    remittance_info: Optional[str] = None

class FedNowRFPRequest(BaseModel):
    rfp_id: Optional[str] = None
    debtor_routing: str
    debtor_name: str
    creditor_routing: str
    creditor_name: str
    amount_cents: int
    expiry_hours: int = 48
    remittance_info: Optional[str] = None

class FedNowTransferResponse(BaseModel):
    end_to_end_id: str
    instruction_id: str
    status: str # ACCP, RJCT, PEND
    status_reason_code: Optional[str] = None
    status_reason_description: Optional[str] = None
    amount_cents: int
    settlement_timestamp: datetime

# --- Master Accounts & Settlement ---
class MasterAccountResponse(BaseModel):
    account_number: str
    routing_number: str
    currency: str
    balance_cents: int
    daylight_overdraft_limit_cents: int
    available_liquidity_cents: int
    status: str
    updated_at: datetime

class MasterAccountAdjustRequest(BaseModel):
    routing_number: str
    adjustment_cents: int # positive to credit, negative to debit
    reason: str

class DailyStatementResponse(BaseModel):
    routing_number: str
    statement_date: date
    opening_balance_cents: int
    closing_balance_cents: int
    ach_debits_cents: int
    ach_credits_cents: int
    fedwire_debits_cents: int
    fedwire_credits_cents: int
    fednow_debits_cents: int
    fednow_credits_cents: int
    total_transactions_count: int

# --- Generic & Health ---
class StatusResponse(BaseModel):
    status: str
    message: Optional[str] = None
    error_code: Optional[str] = None

class HealthResponse(BaseModel):
    status: str
    service: str = "mock-fed-gateway"
    version: str = "2.0.0"
    districts_count: int
    institutions_count: int
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest mock-fed-gateway/tests/test_schemas.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add mock-fed-gateway/schemas.py mock-fed-gateway/tests/test_schemas.py
git commit -m "feat(fed-gateway): add robust Pydantic schemas for Fed Directory, ACH, Fedwire RTGS, FedNow, and Master Account APIs"
```

---

### Task 5: E-Payments Routing Directory & Bank Registry Router

**Files:**
- Create: `mock-fed-gateway/routers/directory.py`
- Test: `mock-fed-gateway/tests/test_directory_router.py`

**Interfaces:**
- Produces:
  - `GET /fed/directory/institutions`
  - `GET /fed/directory/routing/{routing_number}`
  - `GET /fed/districts`
  - `GET /banks`

- [ ] **Step 1: Write failing test for directory endpoints**

```python
# mock-fed-gateway/tests/test_directory_router.py
import pytest
from httpx import AsyncClient, ASGITransport
from main import app

@pytest.mark.asyncio
async def test_get_districts():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/fed/districts")
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 12
        assert any(d["name"] == "Federal Reserve Bank of New York" for d in data)

@pytest.mark.asyncio
async def test_get_banks_backward_compat():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/banks")
        assert res.status_code == 200
        data = res.json()
        assert "banks" in data
        assert len(data["banks"]) > 0

@pytest.mark.asyncio
async def test_routing_lookup():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/fed/directory/routing/021000021")
        assert res.status_code == 200
        data = res.json()
        assert data["valid"] is True
        assert data["institution"]["name"] == "JPMorgan Chase Bank, N.A."
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest mock-fed-gateway/tests/test_directory_router.py -v`
Expected: FAIL

- [ ] **Step 3: Implement routers/directory.py**

```python
# mock-fed-gateway/routers/directory.py
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func
from database import get_db
from models import FederalReserveDistrict, Institution
from schemas import (
    DistrictOut,
    InstitutionOut,
    DirectorySearchResponse,
    RoutingLookupResponse,
    BankListResponse,
    BankSimple,
)
from routing_utils import validate_routing_number, format_routing_number

router = APIRouter(tags=["E-Payments Directory"])

@router.get("/fed/districts", response_model=list[DistrictOut])
async def get_fed_districts(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(FederalReserveDistrict).order_id(FederalReserveDistrict.id))
    return res.scalars().all()

@router.get("/fed/directory/institutions", response_model=DirectorySearchResponse)
async def search_institutions(
    q: Optional[str] = Query(None, description="Search by name, short name, or routing number prefix"),
    state: Optional[str] = Query(None, max_length=2),
    district_id: Optional[int] = Query(None, ge=1, le=12),
    fedach_only: bool = False,
    fedwire_only: bool = False,
    fednow_only: bool = False,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    query = select(Institution)
    count_query = select(func.count()).select_from(Institution)

    if q:
        search_pattern = f"%{q.strip()}%"
        cond = or_(
            Institution.name.ilike(search_pattern),
            Institution.short_name.ilike(search_pattern),
            Institution.routing_number.like(f"{q.strip()}%"),
            Institution.city.ilike(search_pattern),
        )
        query = query.where(cond)
        count_query = count_query.where(cond)

    if state:
        query = query.where(Institution.state == state.upper())
        count_query = count_query.where(Institution.state == state.upper())

    if district_id:
        query = query.where(Institution.district_id == district_id)
        count_query = count_query.where(Institution.district_id == district_id)

    if fedach_only:
        query = query.where(Institution.fedach_participant.is_(True))
        count_query = count_query.where(Institution.fedach_participant.is_(True))

    if fedwire_only:
        query = query.where(Institution.fedwire_participant.is_(True))
        count_query = count_query.where(Institution.fedwire_participant.is_(True))

    if fednow_only:
        query = query.where(Institution.fednow_participant.is_(True))
        count_query = count_query.where(Institution.fednow_participant.is_(True))

    total = (await db.execute(count_query)).scalar_one()
    res = await db.execute(query.order_by(Institution.name).offset(offset).limit(limit))
    institutions = res.scalars().all()

    return DirectorySearchResponse(
        total=total,
        institutions=[InstitutionOut.model_validate(i, from_attributes=True) for i in institutions],
    )

@router.get("/fed/directory/routing/{routing_number}", response_model=RoutingLookupResponse)
async def lookup_routing_number(routing_number: str, db: AsyncSession = Depends(get_db)):
    val = validate_routing_number(routing_number)
    formatted = format_routing_number(routing_number)
    if not val["valid"]:
        return RoutingLookupResponse(
            valid=False,
            routing_number=routing_number,
            formatted=formatted,
            errors=val["errors"],
        )

    res = await db.execute(select(Institution).where(Institution.routing_number == routing_number))
    inst = res.scalar_one_or_none()

    if not inst:
        return RoutingLookupResponse(
            valid=False,
            routing_number=routing_number,
            formatted=formatted,
            errors=["Routing number passes Mod-10 checksum but is not registered in Federal Reserve Directory"],
        )

    dist_res = await db.execute(select(FederalReserveDistrict).where(FederalReserveDistrict.id == inst.district_id))
    dist = dist_res.scalar_one_or_none()

    return RoutingLookupResponse(
        valid=True,
        routing_number=routing_number,
        formatted=formatted,
        institution=InstitutionOut.model_validate(inst, from_attributes=True),
        district=DistrictOut.model_validate(dist, from_attributes=True) if dist else None,
        errors=[],
    )

@router.get("/banks", response_model=BankListResponse)
async def get_banks_compat(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Institution).order_by(Institution.name))
    institutions = res.scalars().all()
    return BankListResponse(
        banks=[BankSimple(name=i.name, routing_number=i.routing_number) for i in institutions]
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest mock-fed-gateway/tests/test_directory_router.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add mock-fed-gateway/routers/directory.py mock-fed-gateway/tests/test_directory_router.py
git commit -m "feat(fed-gateway): implement E-Payments Routing Directory with ABA validation and bank registry endpoints"
```

---

### Task 6: FedACH® Origination & Returns Simulation Engine

**Files:**
- Create: `mock-fed-gateway/routers/ach.py`
- Test: `mock-fed-gateway/tests/test_ach_router.py`

**Interfaces:**
- Produces:
  - `POST /fed/ach/originate`
  - `POST /fed/ach/batches`
  - `GET /fed/ach/transactions/{id}`
  - NACHA return code simulation engine (R01, R02, R03, R04, R08, R10, R16, R20)

- [ ] **Step 1: Write failing test for FedACH origination and return codes**

```python
# mock-fed-gateway/tests/test_ach_router.py
import pytest
from httpx import AsyncClient, ASGITransport
from main import app

@pytest.mark.asyncio
async def test_ach_originate_success():
    payload = {
        "originator_routing": "123400010",
        "originator_name": "Karin Bank",
        "originator_account": "1001",
        "receiver_routing": "021000021",
        "receiver_name": "Chase Customer",
        "receiver_account": "987654321",
        "amount": 100.00,
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/fed/ach/originate", json=payload, headers={"X-API-KEY": "dev_gateway_key_123"})
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "SETTLED"
        assert data["amount_cents"] == 10000
        assert data["trace_number"] is not None

@pytest.mark.asyncio
async def test_ach_return_r01_nsf():
    payload = {
        "originator_routing": "123400010",
        "receiver_routing": "021000021",
        "receiver_account": "987654321",
        "amount": 100.01,  # .01 triggers R01 NSF
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/fed/ach/originate", json=payload, headers={"X-API-KEY": "dev_gateway_key_123"})
        assert res.status_code == 400
        data = res.json()["detail"]
        assert data["error_code"] == "R01"

@pytest.mark.asyncio
async def test_ach_return_r03_no_account():
    payload = {
        "originator_routing": "123400010",
        "receiver_routing": "021000021",
        "receiver_account": "00000123",  # 00000 triggers R03
        "amount": 50.00,
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/fed/ach/originate", json=payload, headers={"X-API-KEY": "dev_gateway_key_123"})
        assert res.status_code == 400
        data = res.json()["detail"]
        assert data["error_code"] == "R03"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest mock-fed-gateway/tests/test_ach_router.py -v`
Expected: FAIL

- [ ] **Step 3: Implement routers/ach.py**

```python
# mock-fed-gateway/routers/ach.py
import uuid
import random
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models import Institution, MasterAccount, ACHTransaction
from schemas import (
    ACHOriginateRequest,
    ACHBatchRequest,
    ACHTransactionResponse,
    ACHBatchResponse,
)
from routing_utils import validate_routing_number

router = APIRouter(prefix="/fed/ach", tags=["FedACH Services"])

RETURN_REASONS = {
    "R01": "Insufficient Funds",
    "R02": "Account Closed",
    "R03": "No Account / Unable to Locate Account",
    "R04": "Invalid Account Number Structure / Routing",
    "R06": "Returned per ODFI Request",
    "R07": "Notice of Change / Authorization Revoked",
    "R08": "Payment Stopped",
    "R10": "Customer Advises Not Authorized",
    "R16": "Account Frozen",
    "R20": "Non-Transaction Account",
}

def determine_ach_return_code(
    amount_cents: int,
    receiver_account: str,
    override_header: str | None = None,
) -> str | None:
    if override_header and override_header in RETURN_REASONS:
        return override_header
    if "00000" in receiver_account:
        return "R03"
    cents_rem = amount_cents % 100
    if cents_rem == 1:
        return "R01"
    if cents_rem == 2:
        return "R02"
    if cents_rem == 8:
        return "R08"
    if cents_rem == 10:
        return "R10"
    if cents_rem == 16:
        return "R16"
    if cents_rem == 20:
        return "R20"
    return None

@router.post("/originate", response_model=ACHTransactionResponse)
async def originate_ach(
    payload: ACHOriginateRequest,
    x_fed_simulate_return: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
):
    orig_rtn = payload.originator_routing or "123400010"
    recv_rtn = payload.receiver_routing or payload.routing_number
    recv_acct = payload.receiver_account or payload.account_number or "100001"

    if not recv_rtn:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": "R04", "message": "Missing receiver routing number"},
        )

    # 1. Validate RTN against Directory
    val = validate_routing_number(recv_rtn)
    if not val["valid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": "R04", "message": f"Invalid routing number: {val['errors']}"},
        )

    res = await db.execute(select(Institution).where(Institution.routing_number == recv_rtn))
    inst = res.scalar_one_or_none()
    if not inst:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "R04", "message": "Receiver institution not found in Fed Directory"},
        )

    # Convert amount to cents
    amount_cents = int(round(payload.amount * 100)) if isinstance(payload.amount, float) else int(payload.amount)

    # 2. Check Failure Triggers
    return_code = determine_ach_return_code(amount_cents, recv_acct, x_fed_simulate_return)
    if return_code:
        reason = RETURN_REASONS.get(return_code, "ACH Return")
        tx_id = str(uuid.uuid4())
        trace_num = f"{recv_rtn[:8]}{random.randint(1000000, 9999999)}"
        ach_entry = ACHTransaction(
            id=tx_id,
            sec_code=payload.sec_code,
            originator_routing=orig_rtn,
            originator_name=payload.originator_name or "Originator",
            originator_account=payload.originator_account or "100001",
            receiver_routing=recv_rtn,
            receiver_name=payload.receiver_name or inst.name,
            receiver_account=recv_acct,
            amount_cents=amount_cents,
            entry_class=payload.entry_class,
            payment_description=payload.payment_description or "ACH Transfer",
            status="RETURNED",
            return_code=return_code,
            return_reason=reason,
            trace_number=trace_num,
        )
        db.add(ach_entry)
        await db.commit()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": return_code, "message": reason, "trace_number": trace_num},
        )

    # 3. Successful ACH settlement
    tx_id = str(uuid.uuid4())
    trace_num = f"{recv_rtn[:8]}{random.randint(1000000, 9999999)}"
    ach_entry = ACHTransaction(
        id=tx_id,
        sec_code=payload.sec_code,
        originator_routing=orig_rtn,
        originator_name=payload.originator_name or "Originator",
        originator_account=payload.originator_account or "100001",
        receiver_routing=recv_rtn,
        receiver_name=payload.receiver_name or inst.name,
        receiver_account=recv_acct,
        amount_cents=amount_cents,
        entry_class=payload.entry_class,
        payment_description=payload.payment_description or "ACH Transfer",
        status="SETTLED",
        trace_number=trace_num,
    )
    db.add(ach_entry)

    # Settle master account balance if available
    res = await db.execute(select(MasterAccount).where(MasterAccount.routing_number == orig_rtn))
    orig_ma = res.scalar_one_or_none()
    res = await db.execute(select(MasterAccount).where(MasterAccount.routing_number == recv_rtn))
    recv_ma = res.scalar_one_or_none()
    if orig_ma and recv_ma:
        if payload.entry_class == "DEBIT":
            orig_ma.balance_cents += amount_cents
            recv_ma.balance_cents -= amount_cents
        else:
            orig_ma.balance_cents -= amount_cents
            recv_ma.balance_cents += amount_cents

    await db.commit()
    await db.refresh(ach_entry)

    return ACHTransactionResponse(
        id=ach_entry.id,
        trace_number=ach_entry.trace_number,
        sec_code=ach_entry.sec_code,
        originator_routing=ach_entry.originator_routing,
        receiver_routing=ach_entry.receiver_routing,
        amount_cents=ach_entry.amount_cents,
        entry_class=ach_entry.entry_class,
        status="SETTLED",
        settlement_date=ach_entry.settlement_date,
        message=f"ACH Origination Settled with {inst.name}",
    )

@router.post("/batches", response_model=ACHBatchResponse)
async def originate_ach_batch(batch: ACHBatchRequest, db: AsyncSession = Depends(get_db)):
    batch_id = f"BATCH-{uuid.uuid4()}"
    settled = 0
    returned = 0
    total_debits = 0
    total_credits = 0
    tx_responses = []

    for entry in batch.entries:
        amt_cents = int(round(entry.amount * 100)) if isinstance(entry.amount, float) else int(entry.amount)
        if entry.entry_class == "DEBIT":
            total_debits += amt_cents
        else:
            total_credits += amt_cents

        return_code = determine_ach_return_code(amt_cents, entry.receiver_account)
        status_val = "RETURNED" if return_code else "SETTLED"
        reason = RETURN_REASONS.get(return_code) if return_code else None

        if status_val == "SETTLED":
            settled += 1
        else:
            returned += 1

        tx_id = str(uuid.uuid4())
        trace_num = f"{entry.receiver_routing[:8]}{random.randint(1000000, 9999999)}"
        ach_entry = ACHTransaction(
            id=tx_id,
            batch_id=batch_id,
            sec_code=entry.sec_code,
            originator_routing=batch.originator_routing,
            originator_name=batch.originator_name,
            originator_account=batch.originator_account,
            receiver_routing=entry.receiver_routing,
            receiver_name=entry.receiver_name,
            receiver_account=entry.receiver_account,
            amount_cents=amt_cents,
            entry_class=entry.entry_class,
            payment_description=entry.payment_description or "Batch ACH",
            status=status_val,
            return_code=return_code,
            return_reason=reason,
            trace_number=trace_num,
        )
        db.add(ach_entry)
        tx_responses.append(ACHTransactionResponse(
            id=tx_id,
            trace_number=trace_num,
            sec_code=entry.sec_code,
            originator_routing=batch.originator_routing,
            receiver_routing=entry.receiver_routing,
            amount_cents=amt_cents,
            entry_class=entry.entry_class,
            status=status_val,
            return_code=return_code,
            return_reason=reason,
            settlement_date=datetime.now(timezone.utc).date(),
        ))

    await db.commit()
    return ACHBatchResponse(
        batch_id=batch_id,
        total_entries=len(batch.entries),
        settled_count=settled,
        returned_count=returned,
        total_debits_cents=total_debits,
        total_credits_cents=total_credits,
        transactions=tx_responses,
    )

@router.get("/transactions/{id}", response_model=ACHTransactionResponse)
async def get_ach_transaction(id: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(ACHTransaction).where(ACHTransaction.id == id))
    tx = res.scalar_one_or_none()
    if not tx:
        raise HTTPException(status_code=404, detail="ACH transaction not found")
    return ACHTransactionResponse.model_validate(tx, from_attributes=True)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest mock-fed-gateway/tests/test_ach_router.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add mock-fed-gateway/routers/ach.py mock-fed-gateway/tests/test_ach_router.py
git commit -m "feat(fed-gateway): implement FedACH single and batch origination engine with NACHA return code triggers"
```

---

### Task 7: Fedwire® Funds Service (RTGS) with IMAD/OMAD Engine

**Files:**
- Create: `mock-fed-gateway/routers/fedwire.py`
- Test: `mock-fed-gateway/tests/test_fedwire_router.py`

**Interfaces:**
- Produces:
  - `POST /fed/wire/originate`
  - `GET /fed/wire/transfers/{imad}`
  - IMAD (`YYYYMMDD{DistrictLetter}1Q{Seq}`) & OMAD generation
  - Daylight overdraft reserve checks

- [ ] **Step 1: Write failing test for Fedwire RTGS transfers**

```python
# mock-fed-gateway/tests/test_fedwire_router.py
import pytest
from httpx import AsyncClient, ASGITransport
from main import app

@pytest.mark.asyncio
async def test_fedwire_originate_success():
    payload = {
        "sender_routing": "123400010",
        "sender_name": "Karin Bank",
        "sender_account": "1001",
        "receiver_routing": "021000021",
        "receiver_name": "Acme Industrial Corp",
        "receiver_account": "987654321",
        "amount_cents": 50000000, # $500,000.00
        "business_function_code": "CTR",
        "payment_reference": "INV-10928",
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/fed/wire/originate", json=payload, headers={"X-API-KEY": "dev_gateway_key_123"})
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "SETTLED"
        assert data["imad"].startswith("2026")
        assert data["omad"].startswith("2026")
        assert data["business_function_code"] == "CTR"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest mock-fed-gateway/tests/test_fedwire_router.py -v`
Expected: FAIL

- [ ] **Step 3: Implement routers/fedwire.py**

```python
# mock-fed-gateway/routers/fedwire.py
import random
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models import Institution, MasterAccount, FedwireTransfer
from schemas import FedwireOriginateRequest, FedwireTransferResponse
from routing_utils import validate_routing_number

router = APIRouter(prefix="/fed/wire", tags=["Fedwire Funds Service (RTGS)"])

def generate_imad(sender_district_id: int) -> str:
    now_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    letters = "ABCDEFGHIJKL"
    district_letter = letters[sender_district_id - 1] if 1 <= sender_district_id <= 12 else "L"
    seq = f"{random.randint(100000, 999999)}{random.randint(1000, 9999)}"
    return f"{now_str}{district_letter}1Q{seq}"

def generate_omad(receiver_district_id: int) -> str:
    now_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    letters = "ABCDEFGHIJKL"
    district_letter = letters[receiver_district_id - 1] if 1 <= receiver_district_id <= 12 else "B"
    seq = f"{random.randint(100000, 999999)}{random.randint(1000, 9999)}"
    return f"{now_str}{district_letter}1Q{seq}"

@router.post("/originate", response_model=FedwireTransferResponse)
async def originate_fedwire(payload: FedwireOriginateRequest, db: AsyncSession = Depends(get_db)):
    # 1. Validate sender and receiver routing numbers
    val_s = validate_routing_number(payload.sender_routing)
    val_r = validate_routing_number(payload.receiver_routing)
    if not val_s["valid"]:
        raise HTTPException(status_code=400, detail=f"Invalid sender routing number: {val_s['errors']}")
    if not val_r["valid"]:
        raise HTTPException(status_code=400, detail=f"Invalid receiver routing number: {val_r['errors']}")

    res = await db.execute(select(Institution).where(Institution.routing_number == payload.sender_routing))
    sender_inst = res.scalar_one_or_none()
    res = await db.execute(select(Institution).where(Institution.routing_number == payload.receiver_routing))
    receiver_inst = res.scalar_one_or_none()

    if not sender_inst:
        raise HTTPException(status_code=404, detail="Sender institution not found in Fed Directory")
    if not receiver_inst:
        raise HTTPException(status_code=404, detail="Receiver institution not found in Fed Directory")

    # 2. Check Sender Master Account reserves & Daylight Overdraft
    res = await db.execute(select(MasterAccount).where(MasterAccount.routing_number == payload.sender_routing))
    sender_ma = res.scalar_one_or_none()
    res = await db.execute(select(MasterAccount).where(MasterAccount.routing_number == payload.receiver_routing))
    receiver_ma = res.scalar_one_or_none()

    if sender_ma:
        available_liquidity = sender_ma.balance_cents + sender_ma.daylight_overdraft_limit_cents
        if payload.amount_cents > available_liquidity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error_code": "EXCEEDS_DAYLIGHT_OVERDRAFT", "message": "Transfer amount exceeds available master account reserve and daylight overdraft headroom"},
            )

    # 3. Generate IMAD / OMAD and settle
    imad = generate_imad(sender_inst.district_id)
    omad = generate_omad(receiver_inst.district_id)
    wire = FedwireTransfer(
        imad=imad,
        omad=omad,
        business_function_code=payload.business_function_code,
        sender_routing=payload.sender_routing,
        sender_name=payload.sender_name,
        sender_account=payload.sender_account,
        receiver_routing=payload.receiver_routing,
        receiver_name=payload.receiver_name,
        receiver_account=payload.receiver_account,
        amount_cents=payload.amount_cents,
        charge_details=payload.charge_details,
        payment_reference=payload.payment_reference,
        status="SETTLED",
    )
    db.add(wire)

    if sender_ma:
        sender_ma.balance_cents -= payload.amount_cents
    if receiver_ma:
        receiver_ma.balance_cents += payload.amount_cents

    await db.commit()
    await db.refresh(wire)

    return FedwireTransferResponse(
        imad=wire.imad,
        omad=wire.omad,
        business_function_code=wire.business_function_code,
        sender_routing=wire.sender_routing,
        receiver_routing=wire.receiver_routing,
        amount_cents=wire.amount_cents,
        status=wire.status,
        settlement_timestamp=wire.settlement_timestamp,
    )

@router.get("/transfers/{imad}", response_model=FedwireTransferResponse)
async def get_fedwire_transfer(imad: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(FedwireTransfer).where(FedwireTransfer.imad == imad))
    wire = res.scalar_one_or_none()
    if not wire:
        raise HTTPException(status_code=404, detail="Fedwire transfer not found")
    return FedwireTransferResponse.model_validate(wire, from_attributes=True)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest mock-fed-gateway/tests/test_fedwire_router.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add mock-fed-gateway/routers/fedwire.py mock-fed-gateway/tests/test_fedwire_router.py
git commit -m "feat(fed-gateway): implement Fedwire RTGS funds transfer with IMAD/OMAD generation and reserve overdraft controls"
```

---

### Task 8: FedNow® Instant Payments & Request for Payment (RFP) Rail

**Files:**
- Create: `mock-fed-gateway/routers/fednow.py`
- Test: `mock-fed-gateway/tests/test_fednow_router.py`

**Interfaces:**
- Produces:
  - `POST /fed/fednow/transfer`
  - `POST /fed/fednow/rfp`
  - `GET /fed/fednow/transfers/{end_to_end_id}`

- [ ] **Step 1: Write failing test for FedNow instant transfers and RFP**

```python
# mock-fed-gateway/tests/test_fednow_router.py
import pytest
from httpx import AsyncClient, ASGITransport
from main import app

@pytest.mark.asyncio
async def test_fednow_transfer_accp():
    payload = {
        "debtor_routing": "123400010",
        "debtor_name": "Ikarin",
        "debtor_account": "1001",
        "creditor_routing": "111000012",
        "creditor_name": "Alex",
        "creditor_account": "2002",
        "amount_cents": 2500, # $25.00
        "remittance_info": "Dinner Split",
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/fed/fednow/transfer", json=payload, headers={"X-API-KEY": "dev_gateway_key_123"})
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ACCP"
        assert data["end_to_end_id"] is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest mock-fed-gateway/tests/test_fednow_router.py -v`
Expected: FAIL

- [ ] **Step 3: Implement routers/fednow.py**

```python
# mock-fed-gateway/routers/fednow.py
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models import Institution, MasterAccount, FedNowTransfer
from schemas import FedNowTransferRequest, FedNowRFPRequest, FedNowTransferResponse
from routing_utils import validate_routing_number

router = APIRouter(prefix="/fed/fednow", tags=["FedNow Instant Payments (24/7/365)"])

@router.post("/transfer", response_model=FedNowTransferResponse)
async def transfer_fednow(payload: FedNowTransferRequest, db: AsyncSession = Depends(get_db)):
    val_d = validate_routing_number(payload.debtor_routing)
    val_c = validate_routing_number(payload.creditor_routing)
    if not val_d["valid"] or not val_c["valid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"status": "RJCT", "status_reason_code": "AGNT", "description": "Incorrect routing identification"},
        )

    res = await db.execute(select(Institution).where(Institution.routing_number == payload.creditor_routing))
    cred_inst = res.scalar_one_or_none()
    if not cred_inst or not cred_inst.fednow_participant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"status": "RJCT", "status_reason_code": "AGNT", "description": "Creditor financial institution is not a FedNow participant"},
        )

    # Rejection trigger: creditor account containing '0000'
    if "0000" in payload.creditor_account:
        end_to_end = payload.end_to_end_id or f"FEDNOW-{uuid.uuid4()}"
        instr_id = payload.instruction_id or f"INSTR-{uuid.uuid4()}"
        tx = FedNowTransfer(
            end_to_end_id=end_to_end,
            instruction_id=instr_id,
            message_type="CREDIT_TRANSFER",
            debtor_routing=payload.debtor_routing,
            debtor_name=payload.debtor_name,
            debtor_account=payload.debtor_account,
            creditor_routing=payload.creditor_routing,
            creditor_name=payload.creditor_name,
            creditor_account=payload.creditor_account,
            amount_cents=payload.amount_cents,
            status="RJCT",
            status_reason_code="AC04",
            status_reason_description="Closed Account Number",
        )
        db.add(tx)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"status": "RJCT", "status_reason_code": "AC04", "description": "Closed Account Number"},
        )

    end_to_end = payload.end_to_end_id or f"FEDNOW-{uuid.uuid4()}"
    instr_id = payload.instruction_id or f"INSTR-{uuid.uuid4()}"
    tx = FedNowTransfer(
        end_to_end_id=end_to_end,
        instruction_id=instr_id,
        message_type="CREDIT_TRANSFER",
        debtor_routing=payload.debtor_routing,
        debtor_name=payload.debtor_name,
        debtor_account=payload.debtor_account,
        creditor_routing=payload.creditor_routing,
        creditor_name=payload.creditor_name,
        creditor_account=payload.creditor_account,
        amount_cents=payload.amount_cents,
        status="ACCP",
    )
    db.add(tx)

    # Immediate settlement of Master Accounts
    res = await db.execute(select(MasterAccount).where(MasterAccount.routing_number == payload.debtor_routing))
    debtor_ma = res.scalar_one_or_none()
    res = await db.execute(select(MasterAccount).where(MasterAccount.routing_number == payload.creditor_routing))
    cred_ma = res.scalar_one_or_none()

    if debtor_ma:
        debtor_ma.balance_cents -= payload.amount_cents
    if cred_ma:
        cred_ma.balance_cents += payload.amount_cents

    await db.commit()
    await db.refresh(tx)

    return FedNowTransferResponse(
        end_to_end_id=tx.end_to_end_id,
        instruction_id=tx.instruction_id,
        status="ACCP",
        amount_cents=tx.amount_cents,
        settlement_timestamp=tx.created_at,
    )

@router.post("/rfp")
async def request_for_payment(payload: FedNowRFPRequest, db: AsyncSession = Depends(get_db)):
    rfp_id = payload.rfp_id or f"RFP-{uuid.uuid4()}"
    tx = FedNowTransfer(
        end_to_end_id=rfp_id,
        instruction_id=f"INSTR-{uuid.uuid4()}",
        message_type="REQUEST_FOR_PAYMENT",
        debtor_routing=payload.debtor_routing,
        debtor_name=payload.debtor_name,
        debtor_account="",
        creditor_routing=payload.creditor_routing,
        creditor_name=payload.creditor_name,
        creditor_account="",
        amount_cents=payload.amount_cents,
        status="PEND",
    )
    db.add(tx)
    await db.commit()
    return {"rfp_id": rfp_id, "status": "PRESENTED_TO_DEBTOR", "amount_cents": payload.amount_cents}

@router.get("/transfers/{end_to_end_id}", response_model=FedNowTransferResponse)
async def get_fednow_transfer(end_to_end_id: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(FedNowTransfer).where(FedNowTransfer.end_to_end_id == end_to_end_id))
    tx = res.scalar_one_or_none()
    if not tx:
        raise HTTPException(status_code=404, detail="FedNow transfer not found")
    return FedNowTransferResponse(
        end_to_end_id=tx.end_to_end_id,
        instruction_id=tx.instruction_id,
        status=tx.status,
        status_reason_code=tx.status_reason_code,
        status_reason_description=tx.status_reason_description,
        amount_cents=tx.amount_cents,
        settlement_timestamp=tx.created_at,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest mock-fed-gateway/tests/test_fednow_router.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add mock-fed-gateway/routers/fednow.py mock-fed-gateway/tests/test_fednow_router.py
git commit -m "feat(fed-gateway): implement FedNow 24/7 instant payment credit transfer and RFP engine"
```

---

### Task 9: Master Account Ledger, Settlement Statements, Main App Wiring & Health

**Files:**
- Create: `mock-fed-gateway/routers/settlement.py`
- Modify: `mock-fed-gateway/main.py`
- Test: `mock-fed-gateway/tests/test_settlement_router.py`
- Test: `mock-fed-gateway/tests/test_main_app.py`

**Interfaces:**
- Produces:
  - `GET /fed/master-account/{routing_number}`
  - `POST /fed/master-account/adjust`
  - `GET /fed/statements/{routing_number}`
  - `GET /health`, `GET /fed/status`, `POST /fed/seed/reset`

- [ ] **Step 1: Write failing test for master accounts and statement generation**

```python
# mock-fed-gateway/tests/test_settlement_router.py
import pytest
from httpx import AsyncClient, ASGITransport
from main import app

@pytest.mark.asyncio
async def test_get_master_account():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/fed/master-account/123400010")
        assert res.status_code == 200
        data = res.json()
        assert data["routing_number"] == "123400010"
        assert data["balance_cents"] > 0
        assert data["status"] == "OPEN"

@pytest.mark.asyncio
async def test_get_statement():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/fed/statements/123400010")
        assert res.status_code == 200
        data = res.json()
        assert data["routing_number"] == "123400010"
        assert "opening_balance_cents" in data
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest mock-fed-gateway/tests/test_settlement_router.py -v`
Expected: FAIL

- [ ] **Step 3: Implement routers/settlement.py and main.py**

```python
# mock-fed-gateway/routers/settlement.py
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from database import get_db
from models import MasterAccount, ACHTransaction, FedwireTransfer, FedNowTransfer
from schemas import (
    MasterAccountResponse,
    MasterAccountAdjustRequest,
    DailyStatementResponse,
)

router = APIRouter(prefix="/fed", tags=["Fed Master Account & Settlement"])

@router.get("/master-account/{routing_number}", response_model=MasterAccountResponse)
async def get_master_account(routing_number: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(MasterAccount).where(MasterAccount.routing_number == routing_number))
    ma = res.scalar_one_or_none()
    if not ma:
        raise HTTPException(status_code=404, detail="Master account not found for institution")
    
    avail = ma.balance_cents + ma.daylight_overdraft_limit_cents
    return MasterAccountResponse(
        account_number=ma.account_number,
        routing_number=ma.routing_number,
        currency=ma.currency,
        balance_cents=ma.balance_cents,
        daylight_overdraft_limit_cents=ma.daylight_overdraft_limit_cents,
        available_liquidity_cents=avail,
        status=ma.status,
        updated_at=ma.updated_at,
    )

@router.post("/master-account/adjust", response_model=MasterAccountResponse)
async def adjust_master_account(payload: MasterAccountAdjustRequest, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(MasterAccount).where(MasterAccount.routing_number == payload.routing_number))
    ma = res.scalar_one_or_none()
    if not ma:
        raise HTTPException(status_code=404, detail="Master account not found for institution")
    
    ma.balance_cents += payload.adjustment_cents
    await db.commit()
    await db.refresh(ma)

    avail = ma.balance_cents + ma.daylight_overdraft_limit_cents
    return MasterAccountResponse(
        account_number=ma.account_number,
        routing_number=ma.routing_number,
        currency=ma.currency,
        balance_cents=ma.balance_cents,
        daylight_overdraft_limit_cents=ma.daylight_overdraft_limit_cents,
        available_liquidity_cents=avail,
        status=ma.status,
        updated_at=ma.updated_at,
    )

@router.get("/statements/{routing_number}", response_model=DailyStatementResponse)
async def get_daily_statement(routing_number: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(MasterAccount).where(MasterAccount.routing_number == routing_number))
    ma = res.scalar_one_or_none()
    if not ma:
        raise HTTPException(status_code=404, detail="Master account not found")

    today = datetime.now(timezone.utc).date()

    # ACH aggregates
    ach_deb = (await db.execute(
        select(func.coalesce(func.sum(ACHTransaction.amount_cents), 0)).where(
            ACHTransaction.originator_routing == routing_number,
            ACHTransaction.entry_class == "DEBIT",
            ACHTransaction.status == "SETTLED",
        )
    )).scalar_one()

    ach_cred = (await db.execute(
        select(func.coalesce(func.sum(ACHTransaction.amount_cents), 0)).where(
            ACHTransaction.receiver_routing == routing_number,
            ACHTransaction.entry_class == "CREDIT",
            ACHTransaction.status == "SETTLED",
        )
    )).scalar_one()

    # Fedwire aggregates
    wire_deb = (await db.execute(
        select(func.coalesce(func.sum(FedwireTransfer.amount_cents), 0)).where(
            FedwireTransfer.sender_routing == routing_number,
            FedwireTransfer.status == "SETTLED",
        )
    )).scalar_one()

    wire_cred = (await db.execute(
        select(func.coalesce(func.sum(FedwireTransfer.amount_cents), 0)).where(
            FedwireTransfer.receiver_routing == routing_number,
            FedwireTransfer.status == "SETTLED",
        )
    )).scalar_one()

    # FedNow aggregates
    now_deb = (await db.execute(
        select(func.coalesce(func.sum(FedNowTransfer.amount_cents), 0)).where(
            FedNowTransfer.debtor_routing == routing_number,
            FedNowTransfer.status == "ACCP",
        )
    )).scalar_one()

    now_cred = (await db.execute(
        select(func.coalesce(func.sum(FedNowTransfer.amount_cents), 0)).where(
            FedNowTransfer.creditor_routing == routing_number,
            FedNowTransfer.status == "ACCP",
        )
    )).scalar_one()

    total_count = (await db.execute(
        select(func.count()).select_from(ACHTransaction).where(ACHTransaction.originator_routing == routing_number)
    )).scalar_one()

    opening = ma.balance_cents + int(wire_deb) + int(now_deb) - int(wire_cred) - int(now_cred)

    return DailyStatementResponse(
        routing_number=routing_number,
        statement_date=today,
        opening_balance_cents=opening,
        closing_balance_cents=ma.balance_cents,
        ach_debits_cents=int(ach_deb),
        ach_credits_cents=int(ach_cred),
        fedwire_debits_cents=int(wire_deb),
        fedwire_credits_cents=int(wire_cred),
        fednow_debits_cents=int(now_deb),
        fednow_credits_cents=int(now_cred),
        total_transactions_count=total_count,
    )
```

```python
# mock-fed-gateway/main.py
import os
import contextlib
import logging
from fastapi import FastAPI, HTTPException, Header, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from database import init_db, AsyncSessionLocal
from seed_data import seed_all_data
from models import FederalReserveDistrict, Institution, ACHTransaction, FedwireTransfer, FedNowTransfer
from routers import directory, ach, fedwire, fednow, settlement
from schemas import HealthResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GATEWAY_API_KEY = os.getenv("GATEWAY_API_KEY", "dev_gateway_key_123")

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing Fed Gateway database...")
    await init_db()
    async with AsyncSessionLocal() as session:
        seed_res = await seed_all_data(session)
        logger.info(f"Seeded Federal Reserve Directory: {seed_res}")
    yield

app = FastAPI(
    title="Karin Bank Mock Federal Reserve Gateway",
    description="High-fidelity Federal Reserve banking simulation (FedACH, Fedwire RTGS, FedNow 24/7, E-Payments Directory)",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Key security dependency for sensitive mutation operations
async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != GATEWAY_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Gateway API Key",
        )
    return x_api_key

# Include Routers
app.include_router(directory.router)
app.include_router(ach.router)
app.include_router(fedwire.router)
app.include_router(fednow.router)
app.include_router(settlement.router)

@app.get("/health", response_model=HealthResponse)
async def health():
    async with AsyncSessionLocal() as session:
        dist_count = (await session.execute(select(func.count()).select_from(FederalReserveDistrict))).scalar_one()
        inst_count = (await session.execute(select(func.count()).select_from(Institution))).scalar_one()
    return HealthResponse(
        status="ok",
        districts_count=dist_count,
        institutions_count=inst_count,
    )

@app.get("/fed/status")
async def fed_status():
    async with AsyncSessionLocal() as session:
        dist_count = (await session.execute(select(func.count()).select_from(FederalReserveDistrict))).scalar_one()
        inst_count = (await session.execute(select(func.count()).select_from(Institution))).scalar_one()
        ach_count = (await session.execute(select(func.count()).select_from(ACHTransaction))).scalar_one()
        wire_count = (await session.execute(select(func.count()).select_from(FedwireTransfer))).scalar_one()
        fednow_count = (await session.execute(select(func.count()).select_from(FedNowTransfer))).scalar_one()
    return {
        "status": "OPERATIONAL",
        "system": "Federal Reserve Core Banking Simulator",
        "statistics": {
            "districts": dist_count,
            "institutions": inst_count,
            "ach_transactions": ach_count,
            "fedwire_transfers": wire_count,
            "fednow_transfers": fednow_count,
        },
    }

@app.post("/fed/seed/reset")
async def reset_seed():
    async with AsyncSessionLocal() as session:
        seed_res = await seed_all_data(session)
    return {"status": "re-seeded", "result": seed_res}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest mock-fed-gateway/tests/ -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add mock-fed-gateway/routers/settlement.py mock-fed-gateway/main.py mock-fed-gateway/tests/
git commit -m "feat(fed-gateway): wire full FastAPI application with settlement statements, health status, and router configuration"
```

---

### Task 10: Docker Compose Build & Live Integration Verification

**Files:**
- Modify: `mock-fed-gateway/requirements.txt` (ensure pytest, httpx, etc. are included)
- Build & Run: `docker compose build mock-fed-gateway && docker compose up -d mock-fed-gateway`

- [ ] **Step 1: Check requirements.txt**

Ensure `fastapi`, `uvicorn`, `sqlalchemy[asyncio]`, `asyncpg`, `pydantic`, `pydantic-settings`, `httpx` are in `mock-fed-gateway/requirements.txt`.

- [ ] **Step 2: Build and restart mock-fed-gateway container**

Run: `docker compose build mock-fed-gateway && docker compose up -d mock-fed-gateway`
Expected: Container builds and starts cleanly.

- [ ] **Step 3: Verify live endpoints via curl**

Run:
1. `curl http://localhost:8002/health`
2. `curl http://localhost:8002/fed/districts`
3. `curl "http://localhost:8002/fed/directory/institutions?limit=5"`
4. `curl http://localhost:8002/fed/directory/routing/021000021`
5. `curl http://localhost:8002/banks`
6. `curl http://localhost:8000/banks` (verify backend proxy works seamlessly)

- [ ] **Step 4: Commit**

```bash
git add mock-fed-gateway/requirements.txt
git commit -m "chore(fed-gateway): update requirements and verify live docker container operation"
```
