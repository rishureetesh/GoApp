import json
from fastapi import APIRouter, Depends

from pydantic import BaseModel
from typing import List, Optional

from starlette.exceptions import HTTPException
from starlette.status import HTTP_400_BAD_REQUEST
from src.config.database import DataAggregation, DataWriter, DeleteData, SingleDataReader, UpdateWriter
from src.models.api_schemas import UpdatedAt
from src.models.models import CurrencyDb

# from src.prisma import prisma
from src.utils.permissions import validate_jwt_token, SuperAdminAccess
from src.utils.permissions import JWTRequired, OrgStaffAccess

router = APIRouter()


class Currency(BaseModel):
    name: str
    abr: str
    symbol: str


class UpdateCurrency(BaseModel):
    name: Optional[str]
    abr: Optional[str]
    symbol: Optional[str]


@router.get("/currency", tags=["currency"], dependencies=[Depends(JWTRequired), Depends(OrgStaffAccess)])
async def get_all_currencies(user=Depends(validate_jwt_token)):
    pipeline = [
        {
            '$lookup': {
                'from': 'WorkOrder',
                'localField': 'id',
                'foreignField': 'currencyId',
                'as': 'workOrders'
            }
        },
        {
            '$lookup': {
                'from': 'Payment',
                'localField': 'id',
                'foreignField': 'currencyId',
                'as': 'payments'
            }
        },
        {
            '$lookup': {
                'from': 'Expense',
                'localField': 'id',
                'foreignField': 'currencyId',
                'as': 'expenses'
            }
        },
        {
            '$lookup': {
                'from': 'Organization',
                'localField': 'id',
                'foreignField': 'defaultCurrencyId',
                'as': 'defaultCurrencyOrganization'
            }
        },
        {
            "$project": {
                "_id": 0
            }
        },
        {
            "$unset": ["defaultCurrencyOrganization._id", "expenses._id", "payments._id", "workOrders._id"]
        }
    ]

    return DataAggregation("Currency", pipeline)


@router.post("/currency", tags=["currency"], dependencies=[Depends(JWTRequired), Depends(SuperAdminAccess)])
async def create_currency(currency: Currency, user=Depends(validate_jwt_token)):
    existing_currency = SingleDataReader("Currency",
                                         {"name": currency.name, "abr": currency.abr, "symbol": currency.symbol})
    if existing_currency:
        raise HTTPException(
            detail=f"Currency of this configuration already exists",
            status_code=HTTP_400_BAD_REQUEST,
        )

    created_currency = CurrencyDb(**currency.dict())
    DataWriter("Currency", created_currency.dict())
    return created_currency


@router.get("/currency/{currency_id}", tags=["currency"], dependencies=[Depends(JWTRequired), Depends(OrgStaffAccess)])
async def get_currency_by_id(currency_id: str, user=Depends(validate_jwt_token)):

    pipeline = [
        {"$match": {"id": currency_id}},
        {
            '$lookup': {
                'from': 'WorkOrder',
                'localField': 'id',
                'foreignField': 'currencyId',
                'as': 'workOrders'
            }
        },
        {
            '$lookup': {
                'from': 'Payment',
                'localField': 'id',
                'foreignField': 'currencyId',
                'as': 'payments'
            }
        },
        {
            '$lookup': {
                'from': 'Expense',
                'localField': 'id',
                'foreignField': 'currencyId',
                'as': 'expenses'
            }
        },
        {
            '$lookup': {
                'from': 'Organization',
                'localField': 'id',
                'foreignField': 'defaultCurrencyId',
                'as': 'defaultCurrencyOrganization'
            }
        },
        {
            "$project": {
                "_id": 0
            }
        },
        {
            "$unset": ["defaultCurrencyOrganization._id", "expenses._id", "payments._id", "workOrders._id"]
        }
    ]

    currency = DataAggregation("Currency", pipeline)

    if not currency:
        raise HTTPException(
            detail=f"Invalid Currency ID", status_code=HTTP_400_BAD_REQUEST
        )
    return currency[0]


@router.post("/currency/{currency_id}", tags=["currency"], dependencies=[Depends(JWTRequired), Depends(SuperAdminAccess)])
async def update_currency_by_id(
        currency_id: str, update_info: UpdateCurrency, user=Depends(validate_jwt_token)
):
    currency = SingleDataReader("Currency", {"id": currency_id})
    currency = Currency(**currency)
    if not currency:
        raise HTTPException(
            detail=f"Invalid Currency ID", status_code=HTTP_400_BAD_REQUEST
        )

    update_info.name = update_info.name if update_info.name else currency.name
    update_info.symbol = update_info.symbol if update_info.symbol else currency.symbol
    update_info.abr = update_info.abr if update_info.abr else currency.abr

    existing_currency = SingleDataReader("Currency", {
        "name": update_info.name,
        "abr": update_info.abr,
        "symbol": update_info.symbol,
    }
                                         )
    print(existing_currency)
    if existing_currency:
        raise HTTPException(
            detail=f"Configuration ({update_info.name}-{update_info.abr}-{update_info.symbol}) already exists",
            status_code=HTTP_400_BAD_REQUEST,
        )

    prev_data = {
        "name": currency.name,
        "abr": currency.abr,
        "symbol": currency.symbol,
    }

    if json.dumps(prev_data) != json.dumps(update_info.dict()):
        UpdateWriter("Currency", {"id": currency_id}, {**update_info.dict(), **UpdatedAt().dict()})

    # Pipeline
    pipeline = [
        {"$match": {"id": currency_id}},
        {
            '$lookup': {
                'from': 'WorkOrder',
                'localField': 'id',
                'foreignField': 'currencyId',
                'as': 'workOrders'
            }
        },
        {
            '$lookup': {
                'from': 'Payment',
                'localField': 'id',
                'foreignField': 'currencyId',
                'as': 'payments'
            }
        },
        {
            '$lookup': {
                'from': 'Expense',
                'localField': 'id',
                'foreignField': 'currencyId',
                'as': 'expenses'
            }
        },
        {
            '$lookup': {
                'from': 'Organization',
                'localField': 'id',
                'foreignField': 'defaultCurrencyId',
                'as': 'defaultCurrencyOrganization'
            }
        },
        {
            "$project": {
                "_id": 0
            }
        },
        {
            "$unset": ["defaultCurrencyOrganization._id", "expenses._id", "payments._id", "workOrders._id"]
        }
    ]

    updated_currency = DataAggregation("Currency", pipeline)

    return updated_currency[0]


@router.delete("/currency/{currency_id}", tags=["currency"],
               dependencies=[Depends(JWTRequired), Depends(SuperAdminAccess)])
async def delete_currency_by_id(currency_id: str, user=Depends(validate_jwt_token)):
    currency = SingleDataReader("Currency", {"id": currency_id})
    if not currency:
        raise HTTPException(
            detail=f"Invalid currency ID", status_code=HTTP_400_BAD_REQUEST
        )
    DeleteData("Currency", {"id": currency_id})
    return {"status": "acknowledged"}
