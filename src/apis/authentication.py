import sys
import traceback

from fastapi import APIRouter, Response
from fastapi import Depends, HTTPException
from pydantic import BaseModel
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN

from src.config.database import SingleDataReader, DataWriter, UpdateWriter, DataAggregation
from src.models.api_schemas import UserSignIn, UserTokenInfoResponse, UserSignOut, UserDisplay, \
    UserCreate, \
    AcknowledgeResponse
from src.models.db_models import UserInDb
from src.models.models import User, UserRoles
from src.utils.auth import create_tokens, ACCESS_TOKEN_EXPIRE_MINUTES, \
    REFRESH_TOKEN_EXPIRE_MINUTES, encryptPassword, validatePassword
from src.utils.permissions import TokenRequired, validate_jwt_token, OrgAdminAccess, OrgStaffAccess

router = APIRouter()


class ChangePassword(BaseModel):
    current: str
    new: str


@router.post("/auth/sign-in", tags=["auth"])
async def auth_login(signIn: UserSignIn, response: Response):
    try:
        pipeline = [
            {"$match": {"email": signIn.email}},
            {
                "$lookup": {
                    "from": "Organization",
                    "localField": "orgId",
                    "foreignField": "id",
                    "as": "organization"
                }
            },
            {
                "$lookup": {
                    "from": "Accounts",
                    "localField": "Organization.id",
                    "foreignField": "orgId",
                    "as": "organization.accounts"
                }
            },
            {
                "$unwind": {
                    "path": "$organization",
                    "preserveNullAndEmptyArrays": True
                },
            },
            {
                "$unwind": {
                    "path": "$organization.accounts",
                    "preserveNullAndEmptyArrays": True
                },
            },
            {
                "$project": {
                    "_id": 0,
                    "organization": {
                        "_id": 0
                    },
                    "organization.accounts": {
                        "_id": 0
                    }
                }
            }
        ]

        user = DataAggregation("User", pipeline)[0]
        user_db = UserInDb(**user)

        if not user_db:
            raise HTTPException(detail="Email is not known", status_code=HTTP_403_FORBIDDEN)

        if not user_db.active:
            raise HTTPException(
                detail="Account is not active.", status_code=HTTP_403_FORBIDDEN
            )

        validated = validatePassword(signIn.password, user_db.password)
        del user_db.password
        del user['password']

        if not validated:
            raise HTTPException(detail="Invalid Password", status_code=HTTP_403_FORBIDDEN)

        pipeline = [
            {"$match": {"userId": user_db.id}},
            {
                "$lookup": {
                    "from": "UserRoles",
                    "localField": "userRoleId",
                    "foreignField": "id",
                    "as": "userRoles"
                }
            },
            {
                "$unwind": "$userRoles"
            },
            {
                "$project": {
                    "_id": 0,
                    "roleName": "$userRoles"
                }
            },
            {
                "$unset": ["roleName._id"]
            }
        ]
        user_role = UserRoles(**DataAggregation("UserAssignedRole", pipeline)[0]["roleName"])
        payload = {"sub": user_db.id, "role": user_role.role_name}
        access_token, refresh_token, _ = create_tokens(payload=payload)
        user_data = UserTokenInfoResponse(
            token=dict(
                access_token=access_token,
                refresh_token=refresh_token
            ),
            role=user_role.role_name,
            unique=user_db.id,
            **user
        )
        response.set_cookie(key="access_token", value=access_token, secure=True, httponly=True,
                            max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60)
        response.set_cookie(key="refresh_token", value=refresh_token, secure=True, httponly=True,
                            max_age=REFRESH_TOKEN_EXPIRE_MINUTES * 60)
        return user_data
    except Exception as e:
        ex_type, ex_value, ex_traceback = sys.exc_info()
        print("Exception : ", e)
        print("Exception type : ", ex_type.__name__)
        print("Exception message : ", ex_value)
        traceback.print_exc()


@router.post("/auth/sign-up", response_model=UserDisplay, tags=["auth"], dependencies=[Depends(TokenRequired), Depends(OrgAdminAccess)])
async def sign_up(user: UserCreate):
    user_by_email = SingleDataReader("User", {"email": user.email})
    if user_by_email:
        raise HTTPException(
            detail="E-Mail already exists.", status_code=HTTP_400_BAD_REQUEST
        )
    user_by_phone = SingleDataReader("User", {"phone": user.phone})
    if user_by_phone:
        raise HTTPException(
            detail="Phone already exists.", status_code=HTTP_400_BAD_REQUEST
        )
    user.password = encryptPassword(user.password)
    data = User(**(user.dict())).dict()
    DataWriter("User", data)
    return UserDisplay(**data)


@router.post("/auth/logout", tags=["auth"], dependencies=[Depends(TokenRequired)])
async def auth_logout(response: Response):
    try:
        response.delete_cookie(key="access_token", path="/", domain=None, secure=True, httponly=True)
        response.delete_cookie(key="refresh_token", path="/", domain=None, secure=True, httponly=True)

        return UserSignOut(message="Logged out successfully", logout=True)
    except Exception as e:
        ex_type, ex_value, ex_traceback = sys.exc_info()
        print("Exception : ", e)
        print("Exception type : ", ex_type.__name__)
        print("Exception message : ", ex_value)
        traceback.print_exc()


@router.post("/auth/password", response_model=AcknowledgeResponse, tags=["auth"], dependencies=[Depends(TokenRequired), Depends(OrgStaffAccess)])
async def update_password(
        password_detail: ChangePassword, user: User = Depends(validate_jwt_token)
):
    validated = validatePassword(password_detail.current, user.password)
    if not validated:
        raise HTTPException(
            detail=f"Invalid password!!!", status_code=HTTP_400_BAD_REQUEST
        )
    # await prisma.user.update(
    #     where={"id": user.id}, data={"password": encryptPassword(password_detail.new)}
    # )
    UpdateWriter("User", {"id": user.id}, {"password": encryptPassword(password_detail.new)})
    return AcknowledgeResponse()
