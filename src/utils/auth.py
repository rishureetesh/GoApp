import os
import time
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from jose import jwt, JWTError

jwtSecret = os.environ.get("JWT_SECRET")

ACCESS_TOKEN_EXPIRE_MINUTES = 30  # 30 minutes
REFRESH_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days
ALGORITHM = "HS256"
JWT_SECRET_KEY = "jhvbzgdsujvmzsdnfczjsdy234567Cujsyfnfgbcyud"


def get_utc_timestamp():
    return int(time.time())


def create_tokens(payload):
    access_token_expires = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = datetime.utcnow() + timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES)

    access_token_dict = {**payload, "exp": access_token_expires, "type": "access"}
    access_token = jwt.encode(access_token_dict, JWT_SECRET_KEY, algorithm="HS256")

    refresh_token_dict = {**payload, "exp": refresh_token_expires, "type": "refresh"}
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


def encryptPassword(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def validatePassword(password: str, encrypted: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), encrypted.encode("utf-8"))


# class JWTBearer(HTTPBearer):
#     def __init__(self, auto_error: bool = True):
#         super(JWTBearer, self).__init__(auto_error=auto_error)

#     async def __call__(self, request: Request):
#         credentials: HTTPAuthorizationCredentials = await super(
#             JWTBearer, self
#         ).__call__(request)
#         if credentials:
#             if not credentials.scheme == "Bearer":
#                 raise HTTPException(
#                     status_code=403, detail="Invalid authentication scheme."
#                 )
#             if not self.verify_jwt(credentials.credentials):
#                 raise HTTPException(
#                     status_code=403, detail="Invalid token or expired token."
#                 )
#             return credentials.credentials
#         else:
#             raise HTTPException(status_code=403, detail="Invalid authorization code.")

#     def verify_jwt(self, jwtToken: str) -> bool:
#         isTokenValid: bool = False
#         try:
#             payload = decodeJWT(jwtToken)
#         except Exception as e:
#             payload = None
#         if payload:
#             isTokenValid = True
#         return isTokenValid

