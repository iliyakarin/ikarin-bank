from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from database import Contact, User
from schemas.contacts import ContactCreate, ContactUpdate
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)

async def get_user_contacts(db: AsyncSession, user_id: int):
    result = await db.execute(
        select(Contact)
        .filter(Contact.user_id == user_id)
        .order_by(Contact.contact_name)
    )
    return result.scalars().all()

async def create_user_contact(db: AsyncSession, user_id: int, contact_data: ContactCreate):
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

    # Check for duplicates
    if contact_data.contact_type == "karin":
        result = await db.execute(select(Contact).filter(
            Contact.user_id == user_id, 
            Contact.contact_email == contact_data.contact_email,
            Contact.contact_type == "karin"
        ))
    elif contact_data.contact_type == "merchant":
        result = await db.execute(select(Contact).filter(
            Contact.user_id == user_id,
            Contact.merchant_id == contact_data.merchant_id,
            Contact.subscriber_id == contact_data.subscriber_id
        ))
    else: # bank
        result = await db.execute(select(Contact).filter(
            Contact.user_id == user_id,
            Contact.routing_number == contact_data.routing_number,
            Contact.account_number == contact_data.account_number
        ))
        
    existing = result.scalars().first()
    if existing:
        raise HTTPException(status_code=400, detail="Contact already exists")

    new_contact = Contact(
        user_id=user_id,
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

async def update_user_contact(db: AsyncSession, user_id: int, contact_id: int, contact_data: ContactUpdate):
    result = await db.execute(select(Contact).filter(
        Contact.id == contact_id, 
        Contact.user_id == user_id
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

async def delete_user_contact(db: AsyncSession, user_id: int, contact_id: int):
    result = await db.execute(select(Contact).filter(
        Contact.id == contact_id, 
        Contact.user_id == user_id
    ))
    contact = result.scalars().first()
    
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
        
    await db.delete(contact)
    await db.commit()
    return True
