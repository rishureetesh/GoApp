from pydantic import BaseModel
from datetime import datetime

class UserSignIn(BaseModel):
    email: str
    password: str = None
    api_token: str = None

class UserSignOut(BaseModel):
    message: str

class Token(BaseModel):
    access_token: str
    refresh_token: str

class TokenRefreshed(Token):
    message:str

class UserTokenInfo(BaseModel):
    token:dict
    permission: list
    role: str
    unique: str

def ResponseModel(data, message):
    return {
        "data": [data],
        "code": 200,
        "message": message,
    }