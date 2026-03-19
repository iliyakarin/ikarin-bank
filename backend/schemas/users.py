from pydantic import BaseModel, ConfigDict
from typing import Optional
import datetime

class UserCreate(BaseModel):
    first_name: str
    last_name: str
    email: str
    password: str
    captcha_token: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str

class UserResponse(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str
    backup_email: Optional[str] = None
    role: str
    time_format: str
    date_format: str

    model_config = ConfigDict(from_attributes=True)

class NotificationResponse(BaseModel):
    id: str
    type: str
    title: str
    message: str
    amount: Optional[float] = None
    created_at: datetime.datetime
    link: str

    model_config = ConfigDict(from_attributes=True)

class UserBackupUpdate(BaseModel):
    backup_email: str

class UserPasswordUpdate(BaseModel):
    current_password: str
    new_password: str

class UserPreferencesUpdate(BaseModel):
    time_format: Optional[str] = None
    date_format: Optional[str] = None
