import json
from fastapi import APIRouter, Depends

from pydantic import BaseModel, Field
from typing import List, Optional

from starlette.exceptions import HTTPException
from starlette.status import HTTP_400_BAD_REQUEST
from src.config.database import DataAggregation, DataWriter, DeleteData, SingleDataReader, UpdateWriter
from src.models.api_schemas import UpdatedAt
from src.models.models import AccountInfoDB
from src.utils.auth import get_utc_timestamp

# from src.prisma import prisma
from src.utils.permissions import validate_jwt_token, OrgAdminAccess
from src.utils.permissions import JWTRequired, OrgStaffAccess

router = APIRouter()


class AccountInfo(BaseModel):
    accountName: str
    accountNumber: str
    orgId: str


class UpdateAccountInfo(BaseModel):
    accountName: Optional[str]
    accountNumber: Optional[str]
    orgId: Optional[str]


@router.get("/account", tags=["accounts"], dependencies=[Depends(JWTRequired), Depends(OrgStaffAccess)])
async def get_all_accounts(user=Depends(validate_jwt_token)):

    pipeline = [
        {"$match": {"orgId": user.orgId}},
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
                "from": "Transaction",
                "localField": "id",
                "foreignField": "accountId",
                "as": "transactions"
            }
        },
        {
            "$unwind": "$organization"
        },
        {
            "$project": {
                "_id": 0,
                "transactions": {
                    "_id": 0,
                }
            }
        },
        {
            "$unset": ["organization._id"]
        },
        {"$sort": {"accountNumber": 1}}
    ]
    return DataAggregation("AccountInfo", pipeline)


@router.post("/account", tags=["accounts"], dependencies=[Depends(JWTRequired), Depends(OrgAdminAccess)])
async def create_account(account: AccountInfo):
    organization = SingleDataReader("Organization", {"id": account.orgId})
    if not organization:
        raise HTTPException(
            detail=f"Invalid Organization ID", status_code=HTTP_400_BAD_REQUEST
        )

    created_account = AccountInfoDB(**account.dict())
    DataWriter("AccountInfo", created_account.dict())
    pipeline = [
        {"$match": {"id": created_account.id}},
        {
            "$lookup": {
                "from": "Organization",
                "localField": "orgId",
                "foreignField": "id",
                "as": "organization"
            }
        },
        {
            "$unwind": "$organization"
        },
        {
            "$project": {
                "_id": 0,
            }
        },
        {
            "$unset": ["organization._id"]
        }
    ]
    return DataAggregation("AccountInfo", pipeline)[0]


@router.get("/account/{account_id}", tags=["accounts"], dependencies=[Depends(JWTRequired), Depends(OrgStaffAccess)])
async def get_account_by_id(account_id: str):

    pipeline = [
        {"$match": {"id": account_id}},
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
                "from": "Transaction",
                "localField": "id",
                "foreignField": "accountId",
                "as": "transactions"
            }
        },
        {
            "$unwind": "$organization"
        },
        {
            "$project": {
                "_id": 0,
                "transactions": {
                    "_id": 0,
                }
            }
        },
        {
            "$unset": ["organization._id"]
        }
    ]
    account = DataAggregation("AccountInfo", pipeline)
    if not account:
        raise HTTPException(
            detail=f"Invalid AccountInfo ID", status_code=HTTP_400_BAD_REQUEST
        )
    return account


@router.post("/account/{account_id}", tags=["accounts"], dependencies=[Depends(JWTRequired), Depends(OrgAdminAccess)])
async def update_account_by_id(
        account_id: str, update_info: UpdateAccountInfo
):

    pipeline = [
        {"$match": {"id": account_id}},
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
                "from": "Transaction",
                "localField": "id",
                "foreignField": "accountId",
                "as": "transactions"
            }
        },
        {
            "$unwind": "$organization"
        },
        {
            "$project": {
                "_id": 0,
                "transactions": {
                    "_id": 0,
                }
            }
        },
        {
            "$unset": ["organization._id"]
        }
    ]
    account_detail = DataAggregation("AccountInfo", pipeline)[0]
    account = AccountInfoDB(**account_detail)

    if not account:
        raise HTTPException(
            detail=f"Invalid AccountInfo ID", status_code=HTTP_400_BAD_REQUEST
        )

    if update_info.orgId and update_info.orgId != account.orgId:
        organization = SingleDataReader("Organization", {"id": update_info.orgId})
        if not organization:
            raise HTTPException(
                detail=f"Invalid Organization ID", status_code=HTTP_400_BAD_REQUEST
            )

    update_info.accountName = (
        update_info.accountName if update_info.accountName else account.accountName
    )
    update_info.accountNumber = (
        update_info.accountNumber
        if update_info.accountNumber
        else account.accountNumber
    )
    update_info.orgId = update_info.orgId if update_info.orgId else account.orgId

    prev_data = {
        "accountName": account.accountName,
        "accountNumber": account.accountNumber,
        "orgId": account.orgId,
    }

    if json.dumps(prev_data) != json.dumps(update_info.dict()):
        UpdateWriter("AccountInfo", {"id": account_id}, {**update_info.dict(), **UpdatedAt().dict()})

    pipeline = [
        {"$match": {"id": account_id}},
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
                "from": "Transaction",
                "localField": "id",
                "foreignField": "accountId",
                "as": "transactions"
            }
        },
        {
            "$unwind": "$organization"
        },
        {
            "$project": {
                "_id": 0,
                "transactions": {
                    "_id": 0,
                }
            }
        },
        {
            "$unset": ["organization._id"]
        }
    ]
    updated_account = DataAggregation("AccountInfo", pipeline)[0]

    return updated_account


@router.delete("/account/{account_id}", tags=["accounts"], dependencies=[Depends(JWTRequired), Depends(OrgAdminAccess)])
async def delete_account_by_id(account_id: str):

    pipeline = [
        {"$match": {"id": account_id}},
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
                "from": "Transaction",
                "localField": "id",
                "foreignField": "accountId",
                "as": "transactions"
            }
        },
        {
            "$unwind": "$organization"
        },
        {
            "$project": {
                "_id": 0,
                "transactions": {
                    "_id": 0,
                }
            }
        },
        {
            "$unset": ["organization._id"]
        }
    ]
    account = DataAggregation("AccountInfo", pipeline)

    if not account:
        raise HTTPException(
            detail=f"Invalid AccountInfo ID", status_code=HTTP_400_BAD_REQUEST
        )
    DeleteData("AccountInfo", {"id": account_id})
    return {"status": "acknowledged"}
