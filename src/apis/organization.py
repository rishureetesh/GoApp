import json
from fastapi import APIRouter, Depends

from pydantic import BaseModel
from typing import List, Optional

from starlette.exceptions import HTTPException
from starlette.status import HTTP_400_BAD_REQUEST
from src.config.database import DataAggregation, DataWriter, DeleteData, SingleDataReader, UpdateWriter
from src.models.api_schemas import UpdatedAt
from src.models.models import Organization

# from src.prisma import prisma
from src.utils.permissions import validate_jwt_token, OrgAdminAccess, SuperAdminAccess, JWTRequired, OrgStaffAccess

router = APIRouter()


class CreateOrganization(BaseModel):
    name: str
    abr: str
    registration: str
    addressLine1: str
    addressLine2: str
    addressLine3: Optional[str]
    city: str
    country: str
    zip: str
    defaultCurrencyId: str


class UpdateOrganization(BaseModel):
    name: Optional[str]
    abr: Optional[str]
    registration: Optional[str]
    addressLine1: Optional[str]
    addressLine2: Optional[str]
    addressLine3: Optional[str]
    city: Optional[str]
    country: Optional[str]
    zip: Optional[str]


class UserInfo(BaseModel):
    user_id: str


@router.get("/org", tags=["organization"], dependencies=[Depends(JWTRequired), Depends(SuperAdminAccess)])
async def read_organizations(requestor=Depends(validate_jwt_token)):
    pipeline = [
            {
                "$lookup": {
                    "from": "AccountInfo",
                    "localField": "id",
                    "foreignField": "orgId",
                    "as": "accounts"
                }
            },
            {
                "$lookup": {
                    "from": "Client",
                    "localField": "id",
                    "foreignField": "orgId",
                    "as": "clients"
                }
            },
            {
                "$lookup": {
                    "from": "User",
                    "localField": "id",
                    "foreignField": "orgId",
                    "as": "users"
                }
            },
            {
                "$lookup": {
                    "from": "Currency",
                    "localField": "defaultCurrencyId",
                    "foreignField": "id",
                    "as": "defaultCurrency"
                }
            },
            {
                "$unwind": "$defaultCurrency"
            },
            {
                "$project": {
                    "_id": 0
                }
            },
            {
                "$unset": ["accounts._id", "clients._id", "users._id", "defaultCurrency._id"]
            }
        ]
    return DataAggregation("Organization", pipeline)


@router.post("/org", tags=["organization"], dependencies=[Depends(JWTRequired), Depends(SuperAdminAccess)])
async def create_organization(
    org: CreateOrganization, requestor=Depends(validate_jwt_token)
):
    existing_org = SingleDataReader("Organization", {"abr": org.abr})
    if existing_org:
        raise HTTPException(
            detail=f"Organization with abbreviation {org.abr} already exists",
            status_code=HTTP_400_BAD_REQUEST,
        )
    organization_creation = Organization(**org.dict())
    DataWriter("Organization", organization_creation.dict())
    return organization_creation


@router.get("/org/{org_id}", tags=["organization"], dependencies=[Depends(JWTRequired), Depends(OrgStaffAccess)])
async def read_organizations(org_id: str, requestor=Depends(validate_jwt_token)):
    pipeline = [
            {"$match": {"id": org_id}},
            {
                "$lookup": {
                    "from": "AccountInfo",
                    "localField": "id",
                    "foreignField": "orgId",
                    "as": "accounts"
                }
            },
            {
                "$lookup": {
                    "from": "Client",
                    "localField": "id",
                    "foreignField": "orgId",
                    "as": "clients"
                }
            },
            {
                "$lookup": {
                    "from": "User",
                    "localField": "id",
                    "foreignField": "orgId",
                    "as": "users"
                }
            },
            {
                "$lookup": {
                    "from": "Currency",
                    "localField": "defaultCurrencyId",
                    "foreignField": "id",
                    "as": "defaultCurrency"
                }
            },
            {
                "$unwind": "$defaultCurrency"
            },
            {
                "$project": {
                    "_id": 0
                }
            },
            {
                "$unset": ["accounts._id", "clients._id", "users._id", "defaultCurrency._id"]
            }
        ]
    organization = DataAggregation("Organization", pipeline)
    if not organization:
        raise HTTPException(
            detail="Invalid organization id",
            status_code=HTTP_400_BAD_REQUEST,
        )
    return organization[0]


@router.post("/org/add/{org_id}", tags=["organization"], dependencies=[Depends(JWTRequired), Depends(OrgAdminAccess)])
async def add_user(
    org_id: str, userId: UserInfo, requestor=Depends(validate_jwt_token)
):
    organization = SingleDataReader("Organization", {"id": org_id})
    if not organization:
        raise HTTPException(
            detail="Invalid organization id",
            status_code=HTTP_400_BAD_REQUEST,
        )

    user = SingleDataReader("User", {"id": userId.user_id})
    if not user:
        raise HTTPException(
            detail="Invalid User id",
            status_code=HTTP_400_BAD_REQUEST,
        )
    UpdateWriter("User", {"id": userId.user_id}, {"orgId": org_id, **UpdatedAt().dict()})
    pipeline = [
            {"$match": {"id": org_id}},
            {
                "$lookup": {
                    "from": "AccountInfo",
                    "localField": "id",
                    "foreignField": "orgId",
                    "as": "accounts"
                }
            },
            {
                "$lookup": {
                    "from": "Client",
                    "localField": "id",
                    "foreignField": "orgId",
                    "as": "clients"
                }
            },
            {
                "$lookup": {
                    "from": "User",
                    "localField": "id",
                    "foreignField": "orgId",
                    "as": "users"
                }
            },
            {
                "$project": {
                    "_id": 0
                }
            },
            {
                "$unset": ["accounts._id", "clients._id", "users._id"]
            }
        ]
    organization = DataAggregation("Organization", pipeline)
    for users in organization[0]["users"]:
        del users["password"]

    return organization


@router.post("/org/{org_id}", tags=["organization"], dependencies=[Depends(JWTRequired), Depends(SuperAdminAccess)])
async def update_organizations(
    org_id: str, update_info: UpdateOrganization, requestor=Depends(validate_jwt_token)
):
    organization = SingleDataReader("Organization", {"id": org_id})
    if not organization:
        raise HTTPException(
            detail="Invalid organization id",
            status_code=HTTP_400_BAD_REQUEST,
        )
    organization = Organization(**organization)
    if update_info.abr and organization.abr != update_info.abr:
        existing_organization = SingleDataReader("Organization", {"abr": update_info.abr})
        if existing_organization:
            raise HTTPException(
                detail=f"An Organization with abbreviation {update_info.abr} already exists",
                status_code=HTTP_400_BAD_REQUEST,
            )

    update_info.name = update_info.name if update_info.name else organization.name
    update_info.abr = update_info.abr if update_info.abr else organization.abr
    update_info.registration = (
        update_info.registration
        if update_info.registration
        else organization.registration
    )
    update_info.addressLine1 = (
        update_info.addressLine1
        if update_info.addressLine1
        else organization.addressLine1
    )
    update_info.addressLine2 = (
        update_info.addressLine2
        if update_info.addressLine2
        else organization.addressLine2
    )
    update_info.addressLine3 = (
        update_info.addressLine3
        if update_info.addressLine3
        else organization.addressLine3
    )
    update_info.city = update_info.city if update_info.city else organization.city
    update_info.country = (
        update_info.country if update_info.country else organization.country
    )
    update_info.zip = update_info.zip if update_info.zip else organization.zip

    prev_data = {
        "name": organization.name,
        "abr": organization.abr,
        "registration": organization.registration,
        "addressLine1": organization.addressLine1,
        "addressLine2": organization.addressLine2,
        "addressLine3": organization.addressLine3,
        "city": organization.city,
        "country": organization.country,
        "zip": organization.zip,
    }

    if json.dumps(prev_data) != json.dumps(update_info.dict()):
        UpdateWriter("Organization", {"id": organization.id}, { **update_info.dict(), **UpdatedAt().dict()})
    pipeline = [
            {"$match": {"id": org_id}},
            {
                "$lookup": {
                    "from": "AccountInfo",
                    "localField": "id",
                    "foreignField": "orgId",
                    "as": "accounts"
                }
            },
            {
                "$lookup": {
                    "from": "Client",
                    "localField": "id",
                    "foreignField": "orgId",
                    "as": "clients"
                }
            },
            {
                "$lookup": {
                    "from": "User",
                    "localField": "id",
                    "foreignField": "orgId",
                    "as": "users"
                }
            },
            {
                "$lookup": {
                    "from": "Currency",
                    "localField": "defaultCurrencyId",
                    "foreignField": "id",
                    "as": "defaultCurrency"
                }
            },
            {
                "$unwind": "$defaultCurrency"
            },
            {
                "$project": {
                    "_id": 0
                }
            },
            {
                "$unset": ["accounts._id", "clients._id", "users._id", "defaultCurrency._id"]
            }
        ]
    updated_org = DataAggregation("Organization", pipeline)
    return updated_org[0]


@router.delete("/org/{org_id}", tags=["organization"], dependencies=[Depends(JWTRequired), Depends(SuperAdminAccess)])
async def delete_organizations(org_id: str, requestor=Depends(validate_jwt_token)):
    organization = SingleDataReader("Organization", {"id": org_id})
    if not organization:
        raise HTTPException(
            detail="Invalid organization id",
            status_code=HTTP_400_BAD_REQUEST,
        )
    DeleteData("Organization", {"id": org_id})
    return {"status": "acknowledged"}
