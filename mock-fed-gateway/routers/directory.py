from typing import Optional, List
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

@router.get("/fed/districts", response_model=List[DistrictOut])
async def get_fed_districts(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(FederalReserveDistrict).order_by(FederalReserveDistrict.id))
    districts = res.scalars().all()
    return [DistrictOut.model_validate(d, from_attributes=True) for d in districts]

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
