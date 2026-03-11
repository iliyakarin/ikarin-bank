from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import Session
from database import User, Account, Transaction, PaymentRequest
from account_service import assign_account_credentials
from schemas.users import UserCreate, Token, UserResponse, NotificationResponse, UserBackupUpdate, UserPasswordUpdate, UserPreferencesUpdate
from auth_utils import get_db, get_current_user, create_access_token, get_password_hash, verify_password, ACCESS_TOKEN_EXPIRE_MINUTES
from activity import emit_activity
import datetime
import httpx
import os
import uuid
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

TURNSTILE_SECRET_KEY = os.getenv("TURNSTILE_SECRET_KEY")
ENV = os.getenv("ENV")

async def verify_turnstile(token: str, ip: str = None):
    if ENV != "production": return True
    if not token: return False
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://challenges.cloudflare.com/turnstile/v0/siteverify",
            data={"secret": TURNSTILE_SECRET_KEY, "response": token, "remoteip": ip}
        )
        data = response.json()
        return data.get("success", False)

@router.post("/auth/register", response_model=UserResponse)
async def register(request: Request, user: UserCreate, db: AsyncSession = Depends(get_db)):
    # Verify Turnstile in production (if secret key is set and not using test key)
    if not await verify_turnstile(user.captcha_token, request.client.host):
         raise HTTPException(status_code=400, detail="Invalid captcha")

    result = await db.execute(select(User).filter(User.email == user.email))
    db_user = result.scalars().first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = get_password_hash(user.password)
    new_user = User(
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        password_hash=hashed_password,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # Auto-create an account for the new user
    new_account = Account(user_id=new_user.id, balance=0.00, name="Main Account", is_main=True)
    await assign_account_credentials(db, new_account)
    db.add(new_account)
    await db.commit()

    emit_activity(
        db, 
        new_user.id, 
        "security", 
        "register", 
        "Account registered", 
        {"email": new_user.email},
        ip=None, # No request object here yet, but we could pass it if register had it
        user_agent=None
    )
    await db.commit()

    return new_user


@router.post("/auth/login", response_model=Token)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)
):
    # Turnstile token is usually passed in the body or as a separate header/form field
    # For OAuth2PasswordRequestForm, we check for a custom field or form parameter
    form = await request.form()
    captcha_token = form.get("captcha_token") or form.get("cf-turnstile-response")
    
    if not await verify_turnstile(captcha_token, request.client.host):
        raise HTTPException(status_code=400, detail="Invalid captcha")

    result = await db.execute(select(User).filter(User.email == form_data.username))
    user = result.scalars().first()
    if not user or not verify_password(form_data.password, user.password_hash):
        if user:
            emit_activity(
                db, 
                user.id, 
                "security", 
                "login_failed", 
                "Failed login attempt", 
                {"email": form_data.username},
                ip=request.client.host,
                user_agent=request.headers.get("user-agent")
            )
            await db.commit()
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    access_token = create_access_token(data={"sub": user.email, "role": user.role})

    emit_activity(
        db, 
        user.id, 
        "security", 
        "login", 
        "User logged in", 
        {"email": user.email},
        ip=request.client.host,
        user_agent=request.headers.get("user-agent")
    )
    await db.commit()

    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/auth/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.post("/v1/users/me/backup", response_model=UserResponse)
async def update_backup_email(
    update_data: UserBackupUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check if this email is already used by someone else
    result = await db.execute(select(User).filter(
        (User.email == update_data.backup_email) | 
        (User.backup_email == update_data.backup_email)
    ))
    existing = result.scalars().first()
    
    if existing and existing.id != current_user.id:
        raise HTTPException(status_code=400, detail="This email is already in use by another user")
        
    current_user.backup_email = update_data.backup_email

    emit_activity(
        db, 
        current_user.id, 
        "security", 
        "email_change", 
        "Backup email updated", 
        {
            "new_backup_email": update_data.backup_email[:3] + "***"
        },
        ip=request.client.host,
        user_agent=request.headers.get("user-agent")
    )
    await db.commit()
    await db.refresh(current_user)
    
    return current_user

@router.post("/v1/users/me/password")
async def update_password(
    password_data: UserPasswordUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify current password
    if not verify_password(password_data.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect current password")
        
    if len(password_data.new_password) < 8:
         raise HTTPException(status_code=400, detail="New password must be at least 8 characters long")
         
    # Hash new password and save
    new_hashed_password = get_password_hash(password_data.new_password)
    current_user.password_hash = new_hashed_password

    emit_activity(
        db, 
        current_user.id, 
        "security", 
        "password_change", 
        "Password changed",
        ip=request.client.host,
        user_agent=request.headers.get("user-agent")
    )
    await db.commit()
    
    return {"status": "success"}

@router.patch("/v1/users/me/preferences", response_model=UserResponse)
async def update_preferences(
    pref_data: UserPreferencesUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if pref_data.time_format:
        current_user.time_format = pref_data.time_format
    if pref_data.date_format:
        current_user.date_format = pref_data.date_format
    
    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.post("/auth/logout")
async def logout(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Server-side logout: logs the event and invalidates the session."""
    user_agent = request.headers.get("user-agent", "unknown")
    client_ip = request.client.host

    emit_activity(
        db, 
        current_user.id, 
        "security", 
        "logout", 
        "User logged out", 
        {
            "ip": client_ip,
            "user_agent": user_agent,
        },
        ip=client_ip,
        user_agent=user_agent
    )
    await db.commit()

    # Note: JWTs are stateless. True invalidation requires a token blacklist.
    # For now we log the event; the client must delete the token.
    return {"status": "success", "message": "Logged out successfully"}


@router.get("/v1/users/me/notifications", response_model=List[NotificationResponse])
async def get_notifications(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get the latest 10 notifications (transactions & payment requests)."""
    notifications = []
    
    # 1. Transactions
    result = await db.execute(select(Account).filter(Account.user_id == current_user.id))
    account_ids = [acc.id for acc in result.scalars().all()]
    if account_ids:
        result = await db.execute(
            select(Transaction).filter(
                Transaction.account_id.in_(account_ids),
                Transaction.status != "cancelled"
            ).order_by(Transaction.created_at.desc()).limit(10)
        )
        transactions = result.scalars().all()
        
        for tx in transactions:
            if tx.status == "failed":
                title = "Payment Failed"
                msg = tx.commentary if tx.commentary else "Transaction failed."
            else:
                is_income = tx.amount > 0 and tx.transaction_side == "CREDIT"
                title = "Payment Received" if is_income else "Payment Sent"
                
                if tx.transaction_type == "transfer":
                    if is_income:
                        msg = f"from {tx.merchant.replace('Received from ', '')}" if tx.merchant else "Transfer received"
                    else:
                        msg = f"to {tx.merchant.replace('Transfer to ', '')}" if tx.merchant else "Transfer sent"
                else:
                    msg = f"Merchant: {tx.merchant}" if tx.merchant else "Transaction processed"
                
            notifications.append({
                "id": f"tx_{tx.id}",
                "type": "transaction",
                "title": title,
                "message": msg,
                "amount": float(tx.amount) if tx.amount else None,
                "created_at": tx.created_at,
                "link": "/client/transactions"
            })
            
    # 2. Payment Requests
    result = await db.execute(
        select(PaymentRequest).filter(
            or_(
                PaymentRequest.requester_id == current_user.id,
                PaymentRequest.target_email == current_user.email
            )
        ).order_by(PaymentRequest.created_at.desc()).limit(10)
    )
    requests = result.scalars().all()
    
    for req in requests:
        is_requester = req.requester_id == current_user.id
        if is_requester:
            title = "Request Sent"
            msg = f"You requested ${req.amount} from {req.target_email}"
        else:
            title = "Request Received"
            msg = f"Someone requested ${req.amount} from you"
            
        notifications.append({
            "id": f"pr_{req.id}",
            "type": "payment_request",
            "title": title,
            "message": msg,
            "amount": float(req.amount) if req.amount else None,
            "created_at": req.created_at,
            "link": "/client/send?tab=request"
        })
        
    # Sort by created_at desc
    notifications.sort(key=lambda x: x["created_at"], reverse=True)
    
    return notifications[:10]


