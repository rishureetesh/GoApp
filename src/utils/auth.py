import time, os
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from src import logger
from typing import Optional
from fastapi import Depends, HTTPException, status, Request


ACCESS_TOKEN_EXPIRE_MINUTES = 30  # 30 minutes
REFRESH_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7 # 7 days
ALGORITHM = "HS256"
JWT_SECRET_KEY = "jhvbzgdsujvmzsdnfczjsdy234567Cujsyfnfgbcyud"

def get_utc_timestamp():
    int(time.time())

def create_tokens(payload):

    access_token_expires = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = datetime.utcnow() + timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES)

    access_token_dict = {**payload, "exp":access_token_expires, "type":"access"}
    access_token = jwt.encode(access_token_dict, JWT_SECRET_KEY, algorithm="HS256")

    refresh_token_dict = {**payload, "exp":refresh_token_expires, "type":"refresh"}
    refresh_token = jwt.encode(refresh_token_dict, JWT_SECRET_KEY, algorithm="HS256")
    return access_token, refresh_token, refresh_token_expires

def decode_token(token):
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
        return payload
    except JWTError:
        return None

def check_jwt_expiration(payload, time_minute):
    exp_timestamp = payload.get("exp")
    now = datetime.now(timezone.utc)
    target_timestamp = datetime.timestamp(now + timedelta(minutes=time_minute))
    return target_timestamp > exp_timestamp