from pydantic import BaseModel, Field

from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from src.models.scalar import Gender, WorkOrderType
from src.models.db_models import (
    DbModel,
    UserBase,
    OrganizationInDb
)
from src.utils.auth import get_utc_timestamp


class AcknowledgeResponse(BaseModel):
    status: str = 'acknowledged'


class UserCreate(UserBase):
    password: str


class UserSignIn(BaseModel):
    email: str
    password: str


class UserResetPassword(BaseModel):
    current: str
    new: str


class UserUpdateSelf(BaseModel):
    email: Optional[str]
    name: Optional[str]
    thumbURL: Optional[str]
    photoURL: Optional[str]
    birthDay: Optional[datetime]
    gender: Optional[Gender]
    phone: Optional[str]


class UserUpdateAdmin(BaseModel):
    orgId: Optional[str]
    email: Optional[str]
    name: Optional[str]
    thumbURL: Optional[str]
    photoURL: Optional[str]
    birthDay: Optional[datetime]
    gender: Optional[Gender]
    phone: Optional[str]
    email_verified: Optional[bool]
    phone_verified: Optional[bool]
    active: Optional[bool]
    superUser: Optional[bool]
    staffUser: Optional[bool]


class UserDisplay(DbModel, UserBase):
    organization: Optional[OrganizationInDb]


class UserTokenInfo(UserDisplay):
    token: str


# My Changes
class UserSignOut(BaseModel):
    message: str
    logout: bool = False


class Token(BaseModel):
    access_token: str
    refresh_token: str


class TokenRefreshed(Token):
    message: str


class UserTokenInfoResponse(UserDisplay):
    token: dict
    role: str
    unique: str


def ResponseModel(data, message):
    return {
        "data": [data],
        "code": 200,
        "message": message,
    }


class UpdatedAt(BaseModel):
    updatedAt: int = Field(default_factory=get_utc_timestamp)
