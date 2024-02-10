import json
from fastapi import APIRouter, Depends

from pydantic import BaseModel
from typing import List, Optional

from starlette.exceptions import HTTPException
from starlette.status import HTTP_400_BAD_REQUEST
from src.config.database import DataAggregation, DataWriter, DeleteData, SingleDataReader, UpdateWriter
from src.models.api_schemas import UpdatedAt
from src.models.models import Client

# from src.prisma import prisma
from src.utils.permissions import validate_jwt_token, TokenRequired, OrgStaffAccess, OrgAdminAccess

router = APIRouter()


class CreateClient(BaseModel):
    name: str
    abr: str
    registration: str
    domestic: bool
    internal: bool
    contact_name: str
    contact_email: str
    contact_phone: str
    addressLine1: str
    addressLine2: str
    addressLine3: Optional[str]
    orgId: str
    city: str
    country: str
    zip: str


class UpdateClient(BaseModel):
    name: Optional[str]
    abr: Optional[str]
    registration: Optional[str]
    domestic: Optional[bool]
    internal: Optional[bool]
    contact_name: Optional[str]
    contact_email: Optional[str]
    contact_phone: Optional[str]
    addressLine1: Optional[str]
    addressLine2: Optional[str]
    addressLine3: Optional[str]
    orgId: Optional[str]
    city: Optional[str]
    country: Optional[str]
    zip: Optional[str]
    active: Optional[bool]


@router.get("/client", tags=["clients"], dependencies=[Depends(TokenRequired), Depends(OrgStaffAccess)])
async def read_clients(requestor=Depends(validate_jwt_token)):
    
    pipeline = [
            {"$match": {"orgId": requestor.orgId}},
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
                    "from": "WorkOrder",
                    "localField": "id",
                    "foreignField": "clientId",
                    "as": "workOrders"
                }
            },
            {
                "$unwind": "$organization"
            },
            {
                "$project": {
                    "_id": 0,
                    "workOrders": {
                        "_id": 0,
                    }
                }
            },
            {
                "$unset": ["organization._id"]
            },
            {"$sort": {"createdAt": -1}}
        ]
    return DataAggregation("Client", pipeline)


@router.post("/client", tags=["clients"], dependencies=[Depends(TokenRequired), Depends(OrgAdminAccess)])
async def create_client(client: CreateClient, requestor=Depends(validate_jwt_token)):
    existing_client = SingleDataReader("Client", {"abr": client.abr})
    if existing_client:
        raise HTTPException(
            detail=f"Client with abbreviation {client.abr} already exists",
            status_code=HTTP_400_BAD_REQUEST,
        )

    organization = SingleDataReader("Organization", {"id": client.orgId})
    if not organization:
        raise HTTPException(
            detail="Invalid organization id",
            status_code=HTTP_400_BAD_REQUEST,
        )
    client_data = Client(**client.dict())
    created_client = DataWriter("Client", {**(client_data.dict())})
    
    pipeline = [
            {"$match": {"id": client_data.id}},
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
                    "from": "WorkOrder",
                    "localField": "id",
                    "foreignField": "clientId",
                    "as": "workOrders"
                }
            },
            {
                "$unwind": "$organization"
            },
            {
                "$project": {
                    "_id": 0,
                    "workOrders": {
                        "_id": 0,
                    }
                }
            },
            {
                "$unset": ["organization._id"]
            }
        ]
    created_client = DataAggregation("Client", pipeline)
    return created_client


@router.get("/client/{client_id}", tags=["clients"], dependencies=[Depends(TokenRequired), Depends(OrgStaffAccess)])
async def read_client(client_id: str, requestor=Depends(validate_jwt_token)):
    
    pipeline = [
            {"$match": {"id": client_id}},
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
                    "from": "WorkOrder",
                    "localField": "id",
                    "foreignField": "clientId",
                    "as": "workOrders"
                }
            },
            {
                "$unwind": "$organization"
            },
            {
                "$project": {
                    "_id": 0,
                    "workOrders": {
                        "_id": 0,
                    }
                }
            },
            {
                "$unset": ["organization._id"]
            }
        ]
    client = DataAggregation("Client", pipeline)
    if not client:
        raise HTTPException(
            detail="Invalid client id",
            status_code=HTTP_400_BAD_REQUEST,
        )
    return client[0]


@router.post("/client/{client_id}", tags=["clients"], dependencies=[Depends(TokenRequired), Depends(OrgAdminAccess)])
async def update_organizations(
    client_id: str, update_info: UpdateClient, requestor=Depends(validate_jwt_token)
):
    # client = await prisma.client.find_unique(where={"id": client_id})
    client = SingleDataReader("Client", {"id": client_id})
    if not client:
        raise HTTPException(
            detail="Invalid client id",
            status_code=HTTP_400_BAD_REQUEST,
        )
    client = Client(**client)
    if update_info.abr and client.abr != update_info.abr:
        # existing_client = await prisma.client.find_first(where={"abr": update_info.abr})
        existing_client = SingleDataReader("Client", {"abr": update_info.abr})
        if existing_client:
            raise HTTPException(
                detail=f"A Client with abbreviation {update_info.abr} already exists",
                status_code=HTTP_400_BAD_REQUEST,
            )

    if update_info.orgId and client.orgId != update_info.orgId:
        # existing_organization = await prisma.organization.find_first(
        #     where={"id": update_info.orgId}
        # )
        existing_organization = SingleDataReader("Organization", {"id": update_info.orgId})
        if existing_organization:
            raise HTTPException(
                detail=f"Invalid organization id",
                status_code=HTTP_400_BAD_REQUEST,
            )

    update_info.name = update_info.name if update_info.name else client.name
    update_info.active = (
        update_info.active if update_info.active != None else client.active
    )
    update_info.abr = update_info.abr if update_info.abr else client.abr
    update_info.registration = (
        update_info.registration if update_info.registration else client.registration
    )
    update_info.domestic = (
        update_info.domestic if update_info.domestic != None else client.domestic
    )
    update_info.internal = (
        update_info.internal if update_info.internal != None else client.internal
    )
    update_info.contact_name = (
        update_info.contact_name if update_info.contact_name else client.contact_name
    )
    update_info.contact_email = (
        update_info.contact_email if update_info.contact_email else client.contact_email
    )
    update_info.contact_phone = (
        update_info.contact_phone if update_info.contact_phone else client.contact_phone
    )
    update_info.addressLine1 = (
        update_info.addressLine1 if update_info.addressLine1 else client.addressLine1
    )
    update_info.addressLine2 = (
        update_info.addressLine2 if update_info.addressLine2 else client.addressLine2
    )
    update_info.addressLine3 = (
        update_info.addressLine3 if update_info.addressLine3 else client.addressLine3
    )
    update_info.orgId = update_info.orgId if update_info.orgId else client.orgId
    update_info.city = update_info.city if update_info.city else client.city
    update_info.country = update_info.country if update_info.country else client.country
    update_info.zip = update_info.zip if update_info.zip else client.zip

    prev_data = {
        "name": client.name,
        "abr": client.abr,
        "registration": client.registration,
        "domestic": client.domestic,
        "internal": client.internal,
        "contact_name": client.contact_name,
        "contact_email": client.contact_email,
        "contact_phone": client.contact_phone,
        "addressLine1": client.addressLine1,
        "addressLine2": client.addressLine2,
        "addressLine3": client.addressLine3,
        "orgId": client.orgId,
        "city": client.city,
        "country": client.country,
        "zip": client.zip,
        "active": client.active,
    }

    if json.dumps(prev_data) != json.dumps(update_info.dict()):
        # await prisma.client.update(where={"id": client.id}, data=update_info.dict())
        UpdateWriter("Client", {"id": client.id}, {**update_info.dict(), **UpdatedAt().dict()})

    # updated_client = await prisma.client.find_unique(
    #     where={"id": client_id}, include={"organization": True, "workOrders": True}
    # )
    pipeline = [
            {"$match": {"id": client_id}},
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
                    "from": "WorkOrder",
                    "localField": "id",
                    "foreignField": "clientId",
                    "as": "workOrders"
                }
            },
            {
                "$unwind": "$organization"
            },
            {
                "$project": {
                    "_id": 0,
                    "workOrders": {
                        "_id": 0,
                    }
                }
            },
            {
                "$unset": ["organization._id"]
            }
        ]
    updated_client = DataAggregation("Client", pipeline)
    return updated_client


@router.delete("/client/{client_id}", tags=["clients"], dependencies=[Depends(TokenRequired), Depends(OrgAdminAccess)])
async def delete_client(client_id: str, requestor=Depends(validate_jwt_token)):
    client = SingleDataReader("Client", {"id": client_id})
    if not client:
        raise HTTPException(
            detail="Invalid client id",
            status_code=HTTP_400_BAD_REQUEST,
        )
    DeleteData("Client", {"id": client_id})
    return {"status": "acknowledged"}
