from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from models.user import User
from models.management import Contact
from schemas.contacts import ContactCreate, ContactUpdate
from fastapi import HTTPException, status
import logging

logger = logging.getLogger(__name__)

async def get_user_contacts(db: AsyncSession, user_id: int):
    """Retrieve all contacts for a specific user, ordered by name."""
    result = await db.execute(
        select(Contact)
        .where(Contact.user_id == user_id)
        .order_by(Contact.contact_name)
    )
    return result.scalars().all()

async def create_user_contact(db: AsyncSession, user_id: int, contact_data: ContactCreate):
    """Add a new contact after validation and duplicate check."""
    name = contact_data.contact_name.strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Name is required")

    # Type-specific validation
    c_type = contact_data.contact_type
    if c_type == "karin":
        if not contact_data.contact_email or not contact_data.contact_email.strip():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email is required for KarinBank contacts")
    elif c_type == "merchant":
        if not contact_data.merchant_id or not contact_data.subscriber_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Merchant ID and Subscriber ID are required")
    elif c_type == "bank":
        if not contact_data.routing_number or not contact_data.account_number:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Routing Number and Account Number are required")

    # Duplicate check
    stmt = select(Contact).where(Contact.user_id == user_id)
    if c_type == "karin":
        stmt = stmt.where(Contact.contact_email == contact_data.contact_email, Contact.contact_type == "karin")
    elif c_type == "merchant":
        stmt = stmt.where(Contact.merchant_id == contact_data.merchant_id, Contact.subscriber_id == contact_data.subscriber_id)
    else: # bank
        stmt = stmt.where(Contact.routing_number == contact_data.routing_number, Contact.account_number == contact_data.account_number)

    if (await db.execute(stmt)).scalars().first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Contact already exists")

    new_contact = Contact(
        user_id=user_id, contact_name=name, contact_email=contact_data.contact_email,
        contact_type=c_type, merchant_id=contact_data.merchant_id,
        subscriber_id=contact_data.subscriber_id, bank_name=contact_data.bank_name,
        routing_number=contact_data.routing_number, account_number=contact_data.account_number
    )

    db.add(new_contact)
    await db.commit()
    await db.refresh(new_contact)
    return new_contact

async def update_user_contact(db: AsyncSession, user_id: int, contact_id: int, contact_data: ContactUpdate):
    """Update contact details."""
    contact = (await db.execute(select(Contact).where(Contact.id == contact_id, Contact.user_id == user_id))).scalars().first()
    if not contact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")

    name = contact_data.contact_name.strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Name is required")

    contact.contact_name = name
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
    """Remove a contact from the user's list."""
    contact = (await db.execute(select(Contact).where(Contact.id == contact_id, Contact.user_id == user_id))).scalars().first()
    if not contact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")

    await db.delete(contact)
    await db.commit()
    return True
