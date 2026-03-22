"""Authentication and User Management Router.

This module handles user registration, login, logout, profile management,
password updates, and notifications.
"""
import datetime
import logging
import os
import uuid
import httpx

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload

from database import SessionLocal
from models.user import User
from models.account import Account
from models.transaction import Transaction
from models.transaction import PaymentRequest
from services.account_service import assign_account_credentials
from schemas.users import (
    UserCreate, Token, UserResponse, NotificationResponse, 
    UserBackupUpdate, UserPasswordUpdate, UserPreferencesUpdate
)
from auth_utils import (
    get_db, get_current_user, create_access_token, 
    get_password_hash, verify_password
)
from activity import emit_activity
from money_utils import from_cents
from turnstile import verify_turnstile
from config import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Auth"])

@router.post("/register", response_model=UserResponse)
async def register(request: Request, user: UserCreate, db: AsyncSession = Depends(get_db)):
    """Registers a new user and automatically creates a main account.

    Validates the Turnstile captcha, checks for email uniqueness, hashes the
    password, and initializes a default account with assigned credentials.

    Args:
        request (Request): The incoming request object.
        user (UserCreate): The registration data (schemas.users.UserCreate).
        db (AsyncSession): The database session.

    Returns:
        User: The newly created user object.

    Raises:
        HTTPException: If captcha is invalid or email is already registered.
    """
    if not await verify_turnstile(user.captcha_token, request.client.host):
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid captcha")

    result = await db.execute(select(User).where(User.email == user.email))
    if result.scalars().first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    hashed_password = get_password_hash(user.password)
    new_user = User(
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        password_hash=hashed_password,
    )
    db.add(new_user)
    await db.flush() # Get user ID before proceeding

    # Auto-create an account for the new user
    new_account = Account(user_id=new_user.id, balance=0, name="Main Account", is_main=True)
    await assign_account_credentials(db, new_account)
    db.add(new_account)
    
    emit_activity(
        db,
        new_user.id,
        "security",
        "register",
        "Account registered",
        {"email": new_user.email},
        ip=request.client.host,
        user_agent=request.headers.get("user-agent")
    )
    
    await db.commit()
    await db.refresh(new_user)
    return new_user

@router.post("/login", response_model=Token)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: AsyncSession = Depends(get_db)
):
    """Authenticates a user and returns a JWT access token.

    Validates credentials and Cloudflare Turnstile captcha. Logs the login
    attempt in the activity feed.

    Args:
        request (Request): The incoming request object.
        form_data (OAuth2PasswordRequestForm): The login credentials.
        db (AsyncSession): The database session.

    Returns:
        dict: A dictionary containing the access token and its type.

    Raises:
        HTTPException: If credentials or captcha are invalid.
    """
    form = await request.form()
    captcha_token = form.get("captcha_token") or form.get("cf-turnstile-response")

    if not await verify_turnstile(captcha_token, request.client.host):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid captcha")

    result = await db.execute(select(User).where(User.email == form_data.username))
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
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")

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

@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """Returns the profile details of the currently authenticated user.

    Args:
        current_user (User): The user retrieved from the JWT dependency.

    Returns:
        User: The current user object.
    """
    return current_user

@router.post("/users/me/backup", response_model=UserResponse)
async def update_backup_email(
    update_data: UserBackupUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update or set a backup email address."""
    # Check if this email is already used by someone else
    result = await db.execute(select(User).where(
        or_(
            User.email == update_data.backup_email,
            User.backup_email == update_data.backup_email
        )
    ))
    existing = result.scalars().first()

    if existing and existing.id != current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This email is already in use by another user")

    current_user.backup_email = update_data.backup_email

    emit_activity(
        db,
        current_user.id,
        "security",
        "email_change",
        "Backup email updated",
        {"new_backup_email": update_data.backup_email[:3] + "***"},
        ip=request.client.host,
        user_agent=request.headers.get("user-agent")
    )
    await db.commit()
    await db.refresh(current_user)
    return current_user

@router.post("/users/me/password")
async def update_password(
    password_data: UserPasswordUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Change the user's password."""
    if not verify_password(password_data.current_password, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect current password")

    if len(password_data.new_password) < 8:
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New password must be at least 8 characters long")

    current_user.password_hash = get_password_hash(password_data.new_password)

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

@router.patch("/users/me/preferences", response_model=UserResponse)
async def update_preferences(
    pref_data: UserPreferencesUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update user-specific display preferences."""
    if pref_data.time_format:
        current_user.time_format = pref_data.time_format
    if pref_data.date_format:
        current_user.date_format = pref_data.date_format

    await db.commit()
    await db.refresh(current_user)
    return current_user

@router.post("/logout")
async def logout(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Log the logout event."""
    emit_activity(
        db,
        current_user.id,
        "security",
        "logout",
        "User logged out",
        ip=request.client.host,
        user_agent=request.headers.get("user-agent")
    )
    await db.commit()
    return {"status": "success", "message": "Logged out successfully"}

from services.notification_service import get_user_notifications

@router.get("/users/me/notifications", response_model=List[NotificationResponse])
async def get_notifications(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Fetch recent activity notifications."""
    return await get_user_notifications(db, current_user.id, current_user.email)
