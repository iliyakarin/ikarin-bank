from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from sqlalchemy import select, and_
from typing import List, Optional
from database import User, Contact
from schemas.contacts import ContactCreate, ContactUpdate, ContactResponse
from auth_utils import get_db, get_current_user
import uuid

router = APIRouter()

@router.get("/v1/contacts", response_model=List[ContactResponse])
async def get_contacts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Contact).filter(Contact.user_id == current_user.id).order_by(Contact.contact_name))
    contacts = result.scalars().all()
    return contacts

@router.post("/v1/contacts", response_model=ContactResponse)
async def create_contact(
    contact_data: ContactCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not contact_data.contact_name.strip():
        raise HTTPException(status_code=400, detail="Name is required")
        
    # Validation per type
    if contact_data.contact_type == "karin":
        if not contact_data.contact_email or not contact_data.contact_email.strip():
            raise HTTPException(status_code=400, detail="Email is required for KarinBank contacts")
    elif contact_data.contact_type == "merchant":
        if not contact_data.merchant_id or not contact_data.subscriber_id:
            raise HTTPException(status_code=400, detail="Merchant ID and Subscriber ID are required")
    elif contact_data.contact_type == "bank":
        if not contact_data.routing_number or not contact_data.account_number:
            raise HTTPException(status_code=400, detail="Routing Number and Account Number are required")

    # Check for duplicates (simplified check based on type and unique identifiers)
    if contact_data.contact_type == "karin":
        result = await db.execute(select(Contact).filter(
            Contact.user_id == current_user.id, 
            Contact.contact_email == contact_data.contact_email,
            Contact.contact_type == "karin"
        ))
    elif contact_data.contact_type == "merchant":
        result = await db.execute(select(Contact).filter(
            Contact.user_id == current_user.id,
            Contact.merchant_id == contact_data.merchant_id,
            Contact.subscriber_id == contact_data.subscriber_id
        ))
    else: # bank
        result = await db.execute(select(Contact).filter(
            Contact.user_id == current_user.id,
            Contact.routing_number == contact_data.routing_number,
            Contact.account_number == contact_data.account_number
        ))
        
    existing = result.scalars().first()
    if existing:
        raise HTTPException(status_code=400, detail="Contact already exists")

    new_contact = Contact(
        user_id=current_user.id,
        contact_name=contact_data.contact_name,
        contact_email=contact_data.contact_email,
        contact_type=contact_data.contact_type,
        merchant_id=contact_data.merchant_id,
        subscriber_id=contact_data.subscriber_id,
        bank_name=contact_data.bank_name,
        routing_number=contact_data.routing_number,
        account_number=contact_data.account_number
    )
    
    db.add(new_contact)
    await db.commit()
    await db.refresh(new_contact)
    
    return new_contact

@router.put("/v1/contacts/{contact_id}", response_model=ContactResponse)
async def update_contact(
    contact_id: int,
    contact_data: ContactUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Contact).filter(
        Contact.id == contact_id, 
        Contact.user_id == current_user.id
    ))
    contact = result.scalars().first()
    
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
        
    if not contact_data.contact_name.strip():
        raise HTTPException(status_code=400, detail="Name is required")
        
    contact.contact_name = contact_data.contact_name
    contact.contact_email = contact_data.contact_email
    contact.merchant_id = contact_data.merchant_id
    contact.subscriber_id = contact_data.subscriber_id
    contact.bank_name = contact_data.bank_name
    contact.routing_number = contact_data.routing_number
    contact.account_number = contact_data.account_number
    
    await db.commit()
    await db.refresh(contact)
    
    return contact

@router.delete("/v1/contacts/{contact_id}")
async def delete_contact(
    contact_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Contact).filter(
        Contact.id == contact_id, 
        Contact.user_id == current_user.id
    ))
    contact = result.scalars().first()
    
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
        
    await db.delete(contact)
    await db.commit()
    
    return {"status": "success"}

