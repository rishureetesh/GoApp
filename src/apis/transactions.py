import io
import os
from fastapi import APIRouter, Depends, File, Form, UploadFile, Response

from pydantic import BaseModel

from starlette.exceptions import HTTPException
from starlette.status import HTTP_400_BAD_REQUEST
from src.config.database import DataAggregation, DataWriter, MultiDataReader, SingleDataReader, UpdateWriter

# from src.prisma import prisma
from src.models.scalar import TransactionType
from src.models.db_models import (
    PaymentBase,
    ExpenseBase,
    TransactionBase,
    TransactionInDb,
    PaymentInDb,
    ExpenseInDb,
)
from src.utils.permissions import validate_jwt_token
from src.utils.storage import write_to_blob, read_blob

router = APIRouter()


class PayInvoice(BaseModel):
    invoiceId: str
    exchangeRate: float
    description: str
    amount: float
    accountId: str


class Payment(BaseModel):
    exchangeRate: float
    description: str
    amount: float
    accountId: str
    currencyId: str


class Expense(BaseModel):
    exchangeRate: float
    description: str
    amount: float
    accountId: str
    currencyId: str


class RecordTransaction(BaseModel):
    description: str
    amount: float
    accountId: str
    currencyId: str
    transactionType: str
    exchangeRate: float


@router.get("/transactions", tags=["transactions"])
async def get_transactions(requestor=Depends(validate_jwt_token)):
    # transactions = await prisma.transaction.find_many(
    #     where={"account": {"organization": {"id": requestor.orgId}}},
    #     include={
    #         "account": {
    #             "include": {"organization": {"include": {"defaultCurrency": True}}}
    #         },
    #         "payment": {"include": {"currency": True}},
    #         "expense": {"include": {"currency": True}},
    #     },
    #     order={"createdAt": "desc"},
    # )

    pipeline = [
        {
            "$match": {
                "account.organization.id": requestor.orgId
            }
        },
        {
            "$lookup": {
                "from": "Accounts",
                "localField": "accountId",
                "foreignField": "id",
                "as": "account"
            }
        },
        {
            "$lookup": {
                "from": "Organizations",
                "localField": "Account.orgId",
                "foreignField": "id",
                "as": "organization"
            }
        },
        {
            "$lookup": {
                "from": "Currencies",
                "localField": "Account.Organization.defaultCurrencyId",
                "foreignField": "id",
                "as": "defaultCurrency"
            }
        },
        {
            "$lookup": {
                "from": "currencies",
                "localField": "Payment.currencyId",
                "foreignField": "id",
                "as": "payment.currency"
            }
        },
        {
            "$lookup": {
                "from": "Currencies",
                "localField": "expense.currencyId",
                "foreignField": "id",
                "as": "expense.currency"
            }
        },
        {
            "$lookup": {
                "from": "Workorders",
                "localField": "workOrder.id",
                "foreignField": "id",
                "as": "workOrder"
            }
        },
        {"$sort": {"createdAt": -1}}
    ]

    transactions = DataAggregation("Transactions", pipeline)

    transformed_data = []
    for row in transactions:
        transformed_data.append(
            {
                "id": row.id,
                "description": row.expense.description
                if row.expense
                else row.payment.description,
                "accountName": row.account.accountName,
                "accountNumber": row.account.accountNumber,
                "currency": row.account.organization.defaultCurrency.abr,
                "currencySymbol": row.account.organization.defaultCurrency.symbol,
                "debit": row.debit,
                "credit": row.credit,
                "originalCurrency": row.expense.currency.abr
                if row.expense
                else row.payment.currency.abr,
                "originalCurrencySymbol": row.expense.currency.symbol
                if row.expense
                else row.payment.currency.symbol,
                "transaction_date": row.createdAt,
            }
        )
    return transformed_data


@router.post("/transactions/payment/invoice", tags=["transactions"])
async def pay_invoice(payment_info: PayInvoice, requestor=Depends(validate_jwt_token)):
    # invoice = await prisma.invoice.find_unique(
    #     where={"id": payment_info.invoiceId},
    #     include={"workOrder": {"include": {"currency": True}}},
    # )

    pipeline = [
        {"$match": {"id": payment_info.invoiceId}},
        {
            "$lookup": {
                "from": "Workorders",
                "localField": "WorkOrder.id",
                "foreignField": "id",
                "as": "workOrder"
            }
        },
        {
            "$lookup": {
                "from": "Currencies",
                "localField": "WorkOrder.currencyId",
                "foreignField": "id",
                "as": "workOrder.currency"
            }
        }
    ]
    invoice = DataAggregation("Invoice", pipeline)
    payment_data = payment_info.dict()
    payment_data["currencyId"] = invoice.workOrder.currencyId
    del payment_data["accountId"]
    # created_payment = await prisma.payment.create(data=payment_data)
    created_payment = DataWriter("Payment", payment_data)
    # await prisma.transaction.create(
    #     data={
    #         "debit": 0,
    #         "credit": created_payment.amount * created_payment.exchangeRate,
    #         "paymentId": created_payment.id,
    #         "accountId": payment_info.accountId,
    #     }
    # )
    DataWriter("Transaction",
               {
                   "debit": 0,
                   "credit": created_payment.amount * created_payment.exchangeRate,
                   "paymentId": created_payment.id,
                   "accountId": payment_info.accountId,
               }
               )
    return {"status": "transaction recorded"}


@router.post("/transactions/payment", tags=["transactions"])
async def record_payment(payment_info: Payment, requestor=Depends(validate_jwt_token)):
    payment_data = payment_info.dict()
    del payment_data["accountId"]
    # created_payment = await prisma.payment.create(data=payment_data)
    created_payment = DataWriter("Payment", payment_data)
    # await prisma.transaction.create(
    #     data={
    #         "debit": 0,
    #         "credit": created_payment.amount * created_payment.exchangeRate,
    #         "paymentId": created_payment.id,
    #         "accountId": payment_info.accountId,
    #     }
    # )
    DataWriter("Payment",
               {
                   "debit": 0,
                   "credit": created_payment.amount * created_payment.exchangeRate,
                   "paymentId": created_payment.id,
                   "accountId": payment_info.accountId,
               }
               )
    return {"status": "transaction recorded"}


@router.post("/transactions/expense", tags=["transactions"])
async def record_expense(expense_info: Payment, requestor=Depends(validate_jwt_token)):
    expense_data = expense_info.dict()
    del expense_data["accountId"]
    # created_expense = await prisma.expense.create(data=expense_data)
    created_expense = DataWriter("Expense", expense_data)
    # await prisma.transaction.create(
    #     data={
    #         "debit": created_expense.amount * created_expense.exchangeRate,
    #         "credit": 0,
    #         "expenseId": created_expense.id,
    #         "accountId": expense_info.accountId,
    #     }
    # )
    DataWriter("Transaction",
               {
                   "debit": created_expense.amount * created_expense.exchangeRate,
                   "credit": 0,
                   "expenseId": created_expense.id,
                   "accountId": expense_info.accountId,
               }
               )
    return {"status": "transaction recorded"}


@router.post("/transactions/record", tags=["transactions"])
async def record_transaction(
        document: UploadFile = File(..., description="transaction document"),
        description: str = Form(..., description="Transaction Description"),
        type: TransactionType = Form(..., description="Type of expense"),
        currency_id: str = Form(..., description="Currency Id"),
        amount: float = Form(..., description="Amount of the Transaction"),
        exchange_rate: float = Form(..., description="Exchange Rate of the currency"),
        account_id: str = Form(..., description="Account Id"),
        requestor=Depends(validate_jwt_token)
):
    data = {
        "description": description,
        "amount": amount,
        "currencyId": currency_id,
        "exchangeRate": exchange_rate,
    }
    expense, payment = None, None
    content = io.BytesIO(document.file.read())
    extension = os.path.splitext(document.filename)[1]
    if type == TransactionType.expense:
        # expense = await prisma.expense.create(data=data)
        expense = DataWriter("Expense", data)
        t_id = expense.id
    else:
        # payment = await prisma.payment.create(data=data)
        payment = DataWriter("Payment", data)
        t_id = payment.id
    pdf_url = write_to_blob(
        path=f"invoices/{type.value}/{t_id}{extension}", data=content
    )

    if type == TransactionType.expense:
        # expense = await prisma.expense.update(
        #     where={"id": t_id}, data={"docUrl": pdf_url}
        # )
        expense = UpdateWriter("Expense", {"id": t_id}, {"docUrl": pdf_url})
    else:
        # payment = await prisma.payment.update(
        #     where={"id": t_id}, data={"docUrl": pdf_url}
        # )
        payment = UpdateWriter("Payment", {"id": t_id}, {"docUrl": pdf_url})
    # account = await prisma.accountinfo.find_unique(where={"id": account_id})
    account = SingleDataReader("Accounts", {"id": account_id})
    # transaction = await prisma.transaction.create(
    #     data={
    #         "debit": expense.amount * expense.exchangeRate if expense else 0,
    #         "credit": payment.amount * payment.exchangeRate if payment else 0,
    #         "expenseId": expense.id if expense else None,
    #         "paymentId": payment.id if payment else None,
    #         "accountId": account.id,
    #     }
    # )
    transaction = DataWriter("Transaction", {
        "debit": expense.amount * expense.exchangeRate if expense else 0,
        "credit": payment.amount * payment.exchangeRate if payment else 0,
        "expenseId": expense.id if expense else None,
        "paymentId": payment.id if payment else None,
        "accountId": account.id,
    }
                             )
    # transaction = await prisma.transaction.find_unique(
    #     where={"id": transaction.id},
    #     include={
    #         "account": {
    #             "include": {"organization": {"include": {"defaultCurrency": True}}}
    #         },
    #         "payment": {"include": {"currency": True}},
    #         "expense": {"include": {"currency": True}},
    #     },
    # )

    pipeline = [
        {"$match": {"id": transaction.id}},
        {
            "$lookup": {
                "from": "accounts",
                "localField": "accountId",
                "foreignField": "_id",
                "as": "account"
            }
        },
        {
            "$lookup": {
                "from": "organizations",
                "localField": "account.orgId",
                "foreignField": "_id",
                "as": "organization"
            }
        },
        {
            "$lookup": {
                "from": "currencies",
                "localField": "account.organization.defaultCurrencyId",
                "foreignField": "_id",
                "as": "defaultCurrency"
            }
        },
        {
            "$lookup": {
                "from": "currencies",
                "localField": "payment.currencyId",
                "foreignField": "_id",
                "as": "payment.currency"
            }
        },
        {
            "$lookup": {
                "from": "currencies",
                "localField": "expense.currencyId",
                "foreignField": "_id",
                "as": "expense.currency"
            }
        }
    ]

    transaction = DataAggregation("Transaction", pipeline)

    data = {
        "id": transaction.id,
        "description": transaction.expense.description
        if transaction.expense
        else transaction.payment.description,
        "accountName": transaction.account.accountName,
        "accountNumber": transaction.account.accountNumber,
        "currency": transaction.account.organization.defaultCurrency.abr,
        "currencySymbol": transaction.account.organization.defaultCurrency.symbol,
        "debit": transaction.debit,
        "credit": transaction.credit,
        "originalCurrency": transaction.expense.currency.abr
        if transaction.expense
        else transaction.payment.currency.abr,
        "originalCurrencySymbol": transaction.expense.currency.symbol
        if transaction.expense
        else transaction.payment.currency.symbol,
        "transaction_date": transaction.createdAt,
    }
    return data


@router.get("/transactions/document/{transaction_id}", tags=["transactions"])
async def download_document(transaction_id: str, requestor=Depends(validate_jwt_token)):
    # transaction = await prisma.transaction.find_unique(
    #     where={"id": transaction_id},
    #     include={
    #         "account": {
    #             "include": {"organization": {"include": {"defaultCurrency": True}}}
    #         },
    #         "payment": {"include": {"currency": True}},
    #         "expense": {"include": {"currency": True}},
    #     },
    # )

    pipeline = [
        {"$match": {"_id": transaction_id}},
        {
            "$lookup": {
                "from": "accounts",
                "localField": "accountId",
                "foreignField": "_id",
                "as": "account"
            }
        },
        {
            "$lookup": {
                "from": "organizations",
                "localField": "account.orgId",
                "foreignField": "_id",
                "as": "organization"
            }
        },
        {
            "$lookup": {
                "from": "currencies",
                "localField": "account.organization.defaultCurrencyId",
                "foreignField": "_id",
                "as": "defaultCurrency"
            }
        },
        {
            "$lookup": {
                "from": "currencies",
                "localField": "payment.currencyId",
                "foreignField": "_id",
                "as": "payment.currency"
            }
        },
        {
            "$lookup": {
                "from": "currencies",
                "localField": "expense.currencyId",
                "foreignField": "_id",
                "as": "expense.currency"
            }
        }
    ]

    transaction = DataAggregation("Transaction", pipeline)
    if not transaction:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST, detail="Transaction not found"
        )

    document_link = (
        transaction.expense.docUrl
        if transaction.expense
        else transaction.payment.docUrl
    )
    upload_path = "/".join(document_link.split("/")[-3:])
    file_name = upload_path.split("/")[-1]
    doc = read_blob(path=upload_path)

    return Response(
        doc,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={file_name}"},
    )

