import json
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from starlette.exceptions import HTTPException
from starlette.status import HTTP_400_BAD_REQUEST

from src.config.database import DataAggregation, SingleDataReader, UpdateWriter, DeleteData, DataWriter
from src.models.api_schemas import UpdatedAt
from src.models.api_schemas import (
    UserCreate,
    UserDisplay,
    UserUpdateSelf,
)
from src.models.db_models import UserInDb
from src.models.models import User
from src.models.scalar import Gender
from src.utils.auth import encryptPassword
from src.utils.permissions import validate_jwt_token, JWTRequired, SuperAdminAccess, OrgAdminAccess, OrgStaffAccess

router = APIRouter()


class UpdateProfile(BaseModel):
    email: Optional[str]
    name: Optional[str] = None
    gender: Optional[Gender] = None
    phone: Optional[str] = None


class UpdateUser(BaseModel):
    name: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    email_verified: Optional[bool]
    phone_verified: Optional[bool]
    active: Optional[bool]


@router.get("/users/all", response_model=List[UserDisplay], tags=["users"], dependencies=[Depends(JWTRequired), Depends(SuperAdminAccess)])
async def read_all_users(requestor: UserInDb = Depends(validate_jwt_token)):
    # users = await prisma.user.find_many(where={"id": {"not": {"equals": requestor.id}}})
    users = SingleDataReader("User", {"_id": {"$ne": requestor.id}})
    return [UserDisplay(**user.dict()) for user in users]


@router.get("/users/org/{org_id}", response_model=List[UserDisplay], tags=["users"], dependencies=[Depends(JWTRequired), Depends(OrgAdminAccess)])
async def read_users_by_org(
        org_id: str, requestor: UserInDb = Depends(validate_jwt_token)
):
    if requestor.staffUser and org_id != requestor.orgId:
        raise HTTPException(
            detail="Requestor not of the same Organization",
            status_code=HTTP_400_BAD_REQUEST,
        )
    # users = await prisma.user.find_many(
    #     where={"id": {"not": {"equals": requestor.id}}, "orgId": org_id}
    # )
    users = SingleDataReader("User", {"_id": {"$ne": requestor.id}, "orgId": org_id})
    return [UserDisplay(**user.dict()) for user in users]


@router.get("/users/me", response_model=UserDisplay, tags=["users"], dependencies=[Depends(JWTRequired), Depends(OrgStaffAccess)])
async def read_user_me(requestor: UserInDb = Depends(validate_jwt_token)):
    # user = await prisma.user.find_unique(
    #     where={"id": requestor.id},
    #     include={"organization": {"include": {"accounts": True}}},
    # )
    pipeline = [
        {
            "$match": {
                "slug": requestor.id
            }
        },
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
                "from": "AccountInfo",
                "localField": "Organization.id",
                "foreignField": "orgId",
                "as": "accounts"
            }
        },
        {
            "$unset": ["organization._id", "accounts._id"]
        }
    ]
    user = DataAggregation("User", pipeline)
    return UserDisplay(**user.dict())


@router.post("/users/me", response_model=UserDisplay, tags=["users"], dependencies=[Depends(JWTRequired), Depends(OrgStaffAccess)])
async def update_user_me(
        update_info: UserUpdateSelf, requestor: UserInDb = Depends(validate_jwt_token)
):
    if update_info.email and requestor.email != update_info.email:
        # existing_user = await prisma.user.find_first(where={"email": update_info.email})
        existing_user = SingleDataReader("User", {"email": update_info.email})
        if existing_user:
            raise HTTPException(
                detail=f"An user with e-mail {update_info.email} already exists",
                status_code=HTTP_400_BAD_REQUEST,
            )

    if update_info.phone and requestor.phone != update_info.phone:
        # existing_user = await prisma.user.find_first(where={"phone": update_info.phone})
        existing_user = SingleDataReader("User", {"phone": update_info.phone})
        if existing_user:
            raise HTTPException(
                detail=f"An user with phone {update_info.phone} already exists",
                status_code=HTTP_400_BAD_REQUEST,
            )

    update_info.name = update_info.name if update_info.name else requestor.name
    update_info.email = update_info.email if update_info.email else requestor.email
    update_info.phone = update_info.phone if update_info.phone else requestor.phone
    update_info.gender = update_info.gender if update_info.gender else requestor.gender
    update_info.thumbURL = (
        update_info.thumbURL if update_info.thumbURL else requestor.thumbURL
    )
    update_info.photoURL = (
        update_info.photoURL if update_info.photoURL else requestor.photoURL
    )
    update_info.birthDay = (
        update_info.birthDay
        if update_info.birthDay.isoformat()
        else requestor.birthDay.isoformat()
    )

    prev_data = {
        "email": requestor.email,
        "name": requestor.name,
        "thumbURL": requestor.thumbURL,
        "photoURL": requestor.photoURL,
        "birthDay": requestor.birthDay.isoformat(),
        "gender": requestor.gender.value,
        "phone": requestor.phone,
    }

    update_data = {
        "email": update_info.email,
        "name": requestor.name,
        "thumbURL": update_info.thumbURL,
        "photoURL": update_info.photoURL,
        "birthDay": update_info.birthDay.isoformat(),
        "gender": update_info.gender.value,
        "phone": update_info.phone,
    }

    if json.dumps(prev_data) != json.dumps(update_data):
        update_data = update_info.dict()
        update_data["gender"] = update_data["gender"].value
        # updated_user = await prisma.user.update(
        #     where={"id": requestor.id}, data=update_data
        # )
        updated_user = UpdateWriter("User", {"id": requestor.id}, update_data)
    # updated_user = await prisma.user.find_unique(
    #     where={"id": requestor.id}, include={"organization": True}
    # )

    pipeline = [
        {
            "$match": {
                "slug": requestor.id
            }
        },
        {
            "$lookup": {
                "from": "Organizations",
                "localField": "organizationId",
                "foreignField": "id",
                "as": "organization"
            }
        }
    ]
    updated_user = DataAggregation("User", pipeline)

    return UserDisplay(**updated_user.dict())


@router.get("/users", response_model=List[UserDisplay], tags=["users"], dependencies=[Depends(JWTRequired), Depends(SuperAdminAccess)])
async def read_users(requestor: UserInDb = Depends(validate_jwt_token)):
    if not requestor.orgId:
        raise HTTPException(
            detail="User does not have associated Organization",
            status_code=HTTP_400_BAD_REQUEST,
        )
    # users = await prisma.user.find_many(
    #     where={"id": {"not": {"equals": requestor.id}}, "orgId": requestor.orgId}
    # )
    users = DataAggregation("User", {"_id": {"$ne": requestor.id}, "orgId": requestor.orgId})
    return [UserDisplay(**user) for user in users]


@router.post("/users/app", response_model=UserDisplay, tags=["users"], dependencies=[Depends(JWTRequired), Depends(SuperAdminAccess)])
async def create_user_app(
        user_info: UserCreate, requestor: UserInDb = Depends(validate_jwt_token)
):
    # existing_user_with_email = await prisma.user.find_first(
    #     where={"email": user_info.email}
    # )
    existing_user_with_email = SingleDataReader("User", {"email": user_info.email})
    if existing_user_with_email:
        raise HTTPException(
            detail="The email is already taken. Cannot use this email.",
            status_code=HTTP_400_BAD_REQUEST,
        )
    # existing_user_with_phone = await prisma.user.find_first(
    #     where={"phone": user_info.phone}
    # )
    existing_user_with_phone = SingleDataReader("User", {"phone": user_info.phone})
    if existing_user_with_phone:
        raise HTTPException(
            detail="The phone is already taken. Cannot use this phone number.",
            status_code=HTTP_400_BAD_REQUEST,
        )
    user_info.password = encryptPassword(user_info.password)
    user_data = user_info.dict()
    user_data["gender"] = user_data["gender"].value
    # created_user = await prisma.user.create(
    #     data=user_data, include={"organization": True}
    # )
    user_data = User(**user_data)
    DataWriter("User", **user_data.dict())
    pipeline = [
        {
            "$match": {
                "id": user_data.id
            }
        },
        {
            "$lookup": {
                "from": "Organization",
                "localField": "orgId",
                "foreignField": "id",
                "as": "organization"
            }
        },
        {
            "$unset": ["organization._id"]
        }
    ]
    user_created = DataAggregation("User", pipeline)
    return UserDisplay(**user_created[0])


@router.post("/users/org", response_model=UserDisplay, tags=["users"], dependencies=[Depends(JWTRequired), Depends(OrgAdminAccess)])
async def create_user_org(
        user_info: UserCreate, requestor: UserInDb = Depends(validate_jwt_token)
):
    user_info.orgId = requestor.orgId
    # existing_user_with_email = await prisma.user.find_first(
    #     where={"email": user_info.email}
    # )
    existing_user_with_email = SingleDataReader("User", {"email": user_info.email})
    if existing_user_with_email:
        raise HTTPException(
            detail="The email is already taken. Cannot use this email.",
            status_code=HTTP_400_BAD_REQUEST,
        )
    # existing_user_with_phone = await prisma.user.find_first(
    #     where={"phone": user_info.phone}
    # )
    existing_user_with_phone = SingleDataReader("User", {"phone": user_info.phone})
    if existing_user_with_phone:
        raise HTTPException(
            detail="The phone is already taken. Cannot use this phone number.",
            status_code=HTTP_400_BAD_REQUEST,
        )
    user_info.password = encryptPassword(user_info.password)
    user_data = User(**user_info.dict())
    # created_user = await prisma.user.create(
    #     data=user_data, include={"organization": True}
    # )
    DataWriter("User", **user_data.dict())
    pipeline = [
        {
            "$match": {
                "id": user_data.id
            }
        },
        {
            "$lookup": {
                "from": "Organization",
                "localField": "orgId",
                "foreignField": "id",
                "as": "organization"
            }
        },
        {
            "$unset": ["organization._id"]
        }
    ]
    user_created = DataAggregation("User", pipeline)
    return UserDisplay(**user_created[0])


@router.get("/users/{userId}", response_model=UserDisplay, tags=["users"], dependencies=[Depends(JWTRequired), Depends(OrgAdminAccess)])
async def read_user(
        userId: str, requestor: UserInDb = Depends(validate_jwt_token)
):
    # user = await prisma.user.find_unique(
    #     where={"id": userId}, include={"organization": True}
    # )
    pipeline = [
        {
            "$match": {
                "id": userId
            }
        },
        {
            "$lookup": {
                "from": "Organization",
                "localField": "orgId",
                "foreignField": "id",
                "as": "organization"
            }
        },
        {
            "$unset": ["organization._id"]
        }
    ]
    user = DataAggregation("User", pipeline)
    if not user:
        raise HTTPException(
            detail="Invalid User ID",
            status_code=HTTP_400_BAD_REQUEST,
        )
    return UserDisplay(user[0])


@router.post("/users/{user_id}", tags=["users"], dependencies=[Depends(JWTRequired), Depends(OrgAdminAccess)])
async def update_user(
        user_id: str,
        update_info: UpdateUser,
        requestor: UserInDb = Depends(validate_jwt_token),
):
    # user = await prisma.user.find_unique(
    #     where={"id": user_id}, include={"organization": True}
    # )
    pipeline = [
        {
            "$match": {
                "id": user_id
            }
        },
        {
            "$lookup": {
                "from": "Organization",
                "localField": "orgId",
                "foreignField": "id",
                "as": "organization"
            }
        },
        {
            "$unset": ["organization._id"]
        }
    ]
    user = DataAggregation("User", pipeline)
    user = User(**user)
    if not user:
        raise HTTPException(
            detail="Invalid User ID",
            status_code=HTTP_400_BAD_REQUEST,
        )

    if user.id == requestor.id:
        raise HTTPException(
            detail="Cannot Update Self, use /apis/user/me to update your details",
            status_code=HTTP_400_BAD_REQUEST,
        )

    if update_info.email and user.email != update_info.email:
        # existing_user = await prisma.user.find_first(where={"email": update_info.email})
        existing_user = SingleDataReader("User", {"email": update_info.email})
        if existing_user:
            raise HTTPException(
                detail=f"An user with e-mail {update_info.email} already exists",
                status_code=HTTP_400_BAD_REQUEST,
            )

    if update_info.phone and user.phone != update_info.phone:
        # existing_user = await prisma.user.find_first(where={"phone": update_info.phone})
        existing_user = SingleDataReader("User", {"email": update_info.phone})
        if existing_user:
            raise HTTPException(
                detail=f"An user with phone {update_info.phone} already exists",
                status_code=HTTP_400_BAD_REQUEST,
            )

    update_info.name = update_info.name if update_info.name else user.name
    update_info.email = update_info.email if update_info.email else user.email
    update_info.phone = update_info.phone if update_info.phone else user.phone
    update_info.email_verified = (
        update_info.email_verified
        if update_info.email_verified
        else user.email_verified
    )
    update_info.phone_verified = (
        update_info.phone_verified
        if update_info.phone_verified
        else user.phone_verified
    )
    update_info.active = update_info.active if update_info.active else user.active

    prev_data = {
        "email": user.email,
        "name": user.name,
        "phone": user.phone,
        "email_verified": user.phone_verified,
        "phone_verified": user.phone_verified,
        "active": user.active,
    }

    if json.dumps(prev_data) != json.dumps(update_info.dict()):
        # await prisma.user.update(where={"id": user.id}, data=update_info.dict())
        UpdateWriter("User", {"id": user.id}, {**update_info.dict(), **UpdatedAt().dict()})

    # updated_user = await prisma.user.find_unique(
    #     where={"id": user_id}, include={"organization": True}
    # )
    pipeline = [
        {
            "$match": {
                "id": user_id
            }
        },
        {
            "$lookup": {
                "from": "Organization",
                "localField": "orgId",
                "foreignField": "id",
                "as": "organization"
            }
        },
        {
            "$unset": ["organization._id"]
        }
    ]
    updated_user = DataAggregation("User", pipeline)
    del updated_user[0]["password"]
    return updated_user


@router.delete("/users/{user_id}", tags=["users"], dependencies=[Depends(JWTRequired), Depends(OrgAdminAccess)])
async def delete_user(user_id: str, requestor: UserInDb = Depends(validate_jwt_token)):
    # user = await prisma.user.find_unique(where={"id": user_id})
    user = SingleDataReader("User", {"id": user_id})
    user = User(**user)

    if not user:
        raise HTTPException(
            detail="Invalid User ID",
            status_code=HTTP_400_BAD_REQUEST,
        )

    if user.id == requestor.id:
        raise HTTPException(
            detail="Cannot delete self",
            status_code=HTTP_400_BAD_REQUEST,
        )
    # await prisma.user.delete(where={"id": user.id})
    DeleteData("User", {"id": user.id})
    return {"status": "acknowledged"}
