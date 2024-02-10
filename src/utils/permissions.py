import sys
import traceback
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from fastapi import Request, Response

from starlette.status import HTTP_401_UNAUTHORIZED
from fastapi import HTTPException, Depends

from src.config.database import SingleDataReader
from src.utils.auth import decode_token
from src.models.db_models import UserInDb


class PermissionConstant:
    SuperAdmin = ["Super Admin"]
    SuperWithOrgAdmin = ["Super Admin", "Org Admin"]
    All = ["Super Admin", "Org Admin", "Org Staff"]
    Custom = ["Super Admin", "Org Staff"]


def get_user_role():
    try:
        pass
    except Exception as e:
        ex_type, ex_value, ex_traceback = sys.exc_info()
        print("Exception : ", e)
        print("Exception type : ", ex_type.__name__)
        print("Exception message : ", ex_value)
        traceback.print_exc()


def JWTRequired(request: Request, response: Response):
    cookies = request.cookies
    refresh_token = cookies.get("refresh_token")

    validated = False

    if refresh_token:

        payload = decode_token(refresh_token)
        exp_timestamp = payload.get("exp")
        now = datetime.now(timezone.utc)
        target_timestamp = int(datetime.timestamp(now + timedelta(seconds=0)))

        if target_timestamp > exp_timestamp:
            response.delete_cookie(key="access_token", path="/", domain=None, secure=True, httponly=True)
            response.delete_cookie(key="refresh_token", path="/", domain=None, secure=True, httponly=True)
        else:
            validated = True
            return refresh_token

    if not validated:
        raise HTTPException(status_code=401, detail="Unauthorized access!")


def TokenRequired(request: Request, response: Response):
    cookies = request.cookies
    refresh_token = cookies.get("refresh_token")

    validated = False

    if refresh_token:

        payload = decode_token(refresh_token)
        exp_timestamp = payload.get("exp")
        now = datetime.now(timezone.utc)
        target_timestamp = int(datetime.timestamp(now + timedelta(seconds=0)))

        if target_timestamp > exp_timestamp:
            response.delete_cookie(key="access_token", path="/", domain=None, secure=True, httponly=True)
            response.delete_cookie(key="refresh_token", path="/", domain=None, secure=True, httponly=True)
        else:
            validated = True
            return refresh_token

    if not validated:
        raise HTTPException(status_code=401, detail="Unauthorized access!")


def JWTOrTokenRequired(request: Request, response: Response):
    validated = False

    cookies = request.cookies
    refresh_token = cookies.get("refresh_token")

    authorization_header = request.headers.get("Authorization")

    if not validated and authorization_header:
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
        raise HTTPException(status_code=401, detail="Unauthorized access!")


def SuperAdminAccess(request: Request):
    cookies = request.cookies
    refresh_token = cookies.get("refresh_token")

    payload = decode_token(refresh_token)
    if payload.get("role") not in PermissionConstant.SuperAdmin:
        raise HTTPException(status_code=403, detail="Access forbidden for non-SuperAdmin")
    return payload


def SuperAdminOrVendorAccess(request: Request):
    cookies = request.cookies
    refresh_token = cookies.get("refresh_token")

    authorization_header = request.headers.get("Authorization")

    Validated = False

    if not Validated and authorization_header:
        API_KEY = authorization_header[7:]
        if API_KEY:
            Validated = True

    payload = decode_token(refresh_token)
    if not Validated and payload.get("role") not in PermissionConstant.SuperAdmin:
        raise HTTPException(status_code=403, detail="Access forbidden for non-SuperAdmin")


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


async def validate_jwt_token(token=Depends(JWTRequired)) -> UserInDb:
    decoded = decode_token(token)
    user_id = decoded.get("sub", None)
    if not user_id:
        raise HTTPException(status_code=403, detail="Malformed authorization code.")
    # user = await prisma.user.find_unique(where={"id": user_id})
    user = SingleDataReader("User", {"id": user_id}, None)
    if not user:
        raise HTTPException(status_code=403, detail="Invalid authorization code.")
    return UserInDb(**user)


async def get_user_details(user_id):
    # user = await prisma.user.find_unique(where={"id": user_id})
    user = SingleDataReader("User", {"id": user_id}, None)
    if not user:
        raise HTTPException(status_code=403, detail="Invalid authorization code.")

    if not user.active:
        raise HTTPException(status_code=403, detail="User is not active")

    return user


async def validate_super_user(token=Depends(JWTRequired)) -> UserInDb:
    decoded = decode_token(token)
    user_id = decoded.get("sub", None)
    if not user_id:
        raise HTTPException(status_code=403, detail="Malformed authorization code.")
    user = await get_user_details(user_id)
    if not user.superUser:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED, detail="Only App Admin Allowed"
        )
    return UserInDb(**user.dict())


async def validate_staff_user(token=Depends(JWTRequired)) -> UserInDb:
    decoded = decode_token(token)
    user_id = decoded.get("sub", None)
    if not user_id:
        raise HTTPException(status_code=403, detail="Malformed authorization code.")
    if not user_id:
        raise HTTPException(status_code=403, detail="Malformed authorization code.")
    user = await get_user_details(user_id)
    if not user.staffUser:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED, detail="Only Organization Admin Allowed"
        )
    if not user.orgId:
        raise HTTPException(
            detail="User does not have associated Organization",
            status_code=403,
        )
    return UserInDb(**user.dict())


async def validate_super_or_staff_user(token=Depends(JWTRequired)) -> UserInDb:
    decoded = decode_token(token)
    user_id = decoded.get("sub", None)
    if not user_id:
        raise HTTPException(status_code=403, detail="Malformed authorization code.")
    user = await get_user_details(user_id)
    if not user.staffUser and not user.superUser:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED, detail="Only Admins Allowed"
        )
    if user.staffUser and not user.orgId:
        raise HTTPException(
            detail="User does not have associated Organization",
            status_code=403,
        )
    return UserInDb(**user.dict())


async def validate_user(token=Depends(JWTRequired)) -> UserInDb:
    decoded = decode_token(token)
    user_id = decoded.get("sub", None)
    if not user_id:
        raise HTTPException(status_code=403, detail="Malformed authorization code.")
    user = await get_user_details(user_id)
    return UserInDb(**user.dict())
