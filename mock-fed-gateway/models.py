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

    def __init__(self, **kwargs):
        kwargs.setdefault("currency", "USD")
        kwargs.setdefault("balance_cents", 1_000_000_000)
        kwargs.setdefault("daylight_overdraft_limit_cents", 500_000_000)
        kwargs.setdefault("status", "OPEN")
        super().__init__(**kwargs)

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

    def __init__(self, **kwargs):
        kwargs.setdefault("sec_code", "PPD")
        kwargs.setdefault("entry_class", "DEBIT")
        kwargs.setdefault("status", "SETTLED")
        super().__init__(**kwargs)

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

    def __init__(self, **kwargs):
        kwargs.setdefault("business_function_code", "CTR")
        kwargs.setdefault("charge_details", "OUR")
        kwargs.setdefault("status", "SETTLED")
        super().__init__(**kwargs)

class FedNowTransfer(Base):
    __tablename__ = "fednow_transfers"

    end_to_end_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    instruction_id: Mapped[str] = mapped_column(String(64), nullable=False)
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

    def __init__(self, **kwargs):
        kwargs.setdefault("message_type", "CREDIT_TRANSFER")
        kwargs.setdefault("status", "ACCP")
        super().__init__(**kwargs)
