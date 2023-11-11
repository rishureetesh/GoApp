from datetime import datetime, timedelta, timezone
from src.utils.auth import create_tokens, decode_token
from fastapi import Request, Response
from fastapi import HTTPException
import traceback, sys
from src import logger

class PermissionConstant:
    SuperAdmin = ["SuperAdmin"]
    SuperWithOrgAdmin = ["SuperAdmin", "OrgAdmin"]
    All = ["SuperAdmin", "OrgAdmin", "OrgStaff"]
    Custom = ["SuperAdmin", "OrgStaff"]

def get_user_role():
    try:
        pass
    except Exception as e:
        ex_type, ex_value, ex_traceback = sys.exc_info()
        print("Exception : ", e)
        print("Exception type : ", ex_type.__name__)
        print("Exception message : ", ex_value)
        traceback.print_exc()


def TokenRequired(request: Request, response: Response):

    validated = False

    cookies = request.cookies
    refresh_token = cookies.get("refresh_token")

    authorization_header = request.headers.get("Authorization")
    user_id = request.headers.get("UserID")

    if not validated and authorization_header and user_id:
        logger.info(f"Validating API key")
        API_KEY = authorization_header[7:]
        if not API_KEY:
            pass
        else:
            validated = True

    if not validated and refresh_token:
        
        payload = decode_token(refresh_token)
        exp_timestamp = payload.get("exp")
        now = datetime.now(timezone.utc)
        target_timestamp = int(datetime.timestamp(now + timedelta(seconds=0)))

        if target_timestamp > exp_timestamp:
            response.delete_cookie(key="access_token", path="/", domain=None, secure=True, httponly=True)
            response.delete_cookie(key="refresh_token", path="/", domain=None, secure=True, httponly=True)
        else:
            validated = True
    
    
    if not validated:
        raise HTTPException(status_code=501, detail="Unauthorized access!")


def SuperAdminAccess(request: Request):

    cookies = request.cookies
    refresh_token = cookies.get("refresh_token")
    
    payload = decode_token(refresh_token)
    if payload.get("role") not in PermissionConstant.SuperAdmin:
        raise HTTPException(status_code=403, detail="Access forbidden for non-SuperAdmin")
    return payload

def OrgAdminAccess(request: Request):

    cookies = request.cookies
    refresh_token = cookies.get("refresh_token")
    
    payload = decode_token(refresh_token)
    if payload.get("role") not in PermissionConstant.SuperWithOrgAdmin:
        raise HTTPException(status_code=403, detail="Access forbidden!!!")
    return payload

def OrgStaffAccess(request: Request):

    cookies = request.cookies
    refresh_token = cookies.get("refresh_token")
    
    payload = decode_token(refresh_token)
    if payload.get("role") not in PermissionConstant.All:
        raise HTTPException(status_code=403, detail="Access forbidden!!!")
    return payload

def CustomAccess(request: Request):

    cookies = request.cookies
    refresh_token = cookies.get("refresh_token")
    
    payload = decode_token(refresh_token)
    if payload.get("role") not in PermissionConstant.Custom:
        raise HTTPException(status_code=403, detail="Access forbidden!!!")
    return payload
