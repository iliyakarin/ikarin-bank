from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from sqlalchemy import select, and_
from typing import List, Optional
from database import User, Contact
from schemas.contacts import ContactCreate, ContactUpdate, ContactResponse
from auth_utils import get_db, get_current_user
import uuid

from services.contact_service import (
    get_user_contacts, create_user_contact, update_user_contact, delete_user_contact
)

router = APIRouter(tags=["Contacts"])

@router.get("/contacts", response_model=List[ContactResponse])
async def get_contacts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve all contacts for the current user."""
    return await get_user_contacts(db, current_user.id)

@router.post("/contacts", response_model=ContactResponse)
async def create_contact(
    contact_data: ContactCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a new contact."""
    return await create_user_contact(db, current_user.id, contact_data)

@router.put("/contacts/{contact_id}", response_model=ContactResponse)
async def update_contact(
    contact_id: int,
    contact_data: ContactUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update an existing contact."""
    return await update_user_contact(db, current_user.id, contact_id, contact_data)

@router.delete("/contacts/{contact_id}")
async def delete_contact(
    contact_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove a contact."""
    await delete_user_contact(db, current_user.id, contact_id)
    return {"status": "success"}

