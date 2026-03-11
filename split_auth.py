import re

with open("backend/main.py", "r") as f:
    text = f.read()

patterns = [
    r"@app\.post\(\"/auth/register\"[\s\S]*?(?=\n@app\.post\(\"/auth/login\")",
    r"@app\.post\(\"/auth/login\"[\s\S]*?(?=\n@app\.get\(\"/auth/me\")",
    r"@app\.get\(\"/auth/me\"[\s\S]*?(?=\n@app\.post\(\"/v1/users/me/backup\")",
    r"@app\.post\(\"/v1/users/me/backup\"[\s\S]*?(?=\n@app\.post\(\"/v1/users/me/password\")",
    r"@app\.post\(\"/v1/users/me/password\"[\s\S]*?(?=\n@app\.patch\(\"/v1/users/me/preferences\")",
    r"@app\.patch\(\"/v1/users/me/preferences\"[\s\S]*?(?=\n@app\.post\(\"/auth/logout\")",
    r"@app\.post\(\"/auth/logout\"[\s\S]*?(?=\n@app\.websocket\(\"/ws/activity)",
    r"@app\.get\(\"/v1/users/me/notifications\"[\s\S]*?(?=\n@app\.get\(\"/accounts/)",
]

routes = []
for p in patterns:
    m = re.search(p, text)
    if m:
        block = m.group(0)
        # replace @app. with @router.
        block = block.replace("@app.", "@router.")
        routes.append(block)
        text = text.replace(m.group(0), "")
    else:
        print("Failed to match:", p[:30])

if routes:
    header = """from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import Session
from database import User, Notification
from schemas.users import UserCreate, Token, UserResponse, NotificationResponse, UserBackupUpdate, UserPasswordUpdate, UserPreferencesUpdate
from auth_utils import get_db, get_current_user, create_access_token, get_password_hash, verify_password, ACCESS_TOKEN_EXPIRE_MINUTES
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

"""
    with open("backend/routers/auth.py", "w") as f:
        f.write(header + "\n".join(routes) + "\n")
    
    text = text.replace("app.include_router(accounts.router)", "app.include_router(accounts.router)\nfrom routers import auth\napp.include_router(auth.router)")
    with open("backend/main.py", "w") as f:
        f.write(text)

