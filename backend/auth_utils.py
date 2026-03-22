"""Authentication and authorization utilities.

This module provides helper functions for password hashing, JWT token creation,
and FastAPI dependencies for user authentication and role-based access control.
"""
import datetime
from datetime import timezone, timedelta
from typing import List, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from config import settings
from database import SessionLocal
from models.user import User

# Auth Configuration
SECRET_KEY = settings.JWT_SECRET_KEY
ALGORITHM = settings.JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="v1/auth/login")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain text password against a hashed password.

    Args:
        plain_password (str): The plain text password to verify.
        hashed_password (str): The bcrypt hashed password to check against.

    Returns:
        bool: True if the passwords match, False otherwise.
    """
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Generates a bcrypt hash for a plain text password.

    Args:
        password (str): The plain text password to hash.

    Returns:
        str: The resulting bcrypt hash.
    """
    return pwd_context.hash(password)

def create_access_token(data: dict) -> str:
    """Creates a new JWT access token.

    Args:
        data (dict): The payload to include in the JWT (typically includes 'sub').

    Returns:
        str: The encoded JWT as a string.
    """
    to_encode = data.copy()
    expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    if isinstance(encoded_jwt, bytes):
        return encoded_jwt.decode("utf-8")
    return str(encoded_jwt)

async def get_db():
    """FastAPI dependency that provides an async database session.

    Yields:
        AsyncSession: A SQLAlchemy async session.
    """
    async with SessionLocal() as db:
        yield db

async def get_current_user(
    token: str = Depends(oauth2_scheme), 
    db: AsyncSession = Depends(get_db)
) -> User:
    """FastAPI dependency that retrieves the currently authenticated user.

    Decodes the JWT token, validates the subject (email), and fetches the user
    from the database.

    Args:
        token (str): The JWT token from the Authorization header.
        db (AsyncSession): The database session.

    Returns:
        User: The authenticated user object.

    Raises:
        HTTPException: If the token is invalid, expired, or the user is not found.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # SQLAlchemy 2.0 style query
    query = select(User).where(User.email == email)
    result = await db.execute(query)
    user = result.scalars().first()
    
    if user is None:
        raise credentials_exception
    return user

class RoleChecker:
    """Dependency for checking if a user has the required roles."""
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have the required permissions for this operation"
            )
        return current_user
