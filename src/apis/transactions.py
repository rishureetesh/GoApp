import io
import os
from fastapi import APIRouter, Depends, File, Form, UploadFile, Response

from pydantic import BaseModel

from starlette.exceptions import HTTPException
from starlette.status import HTTP_400_BAD_REQUEST
from src.config.database import DataAggregation, DataWriter, MultiDataReader, SingleDataReader, UpdateWriter
from src.models.models import PaymentDB, Transaction, ExpenseDB

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
from src.utils.permissions import validate_jwt_token, JWTRequired, OrgAdminAccess
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


@router.get("/transactions", tags=["transactions"], dependencies=[Depends(JWTRequired), Depends(OrgAdminAccess)])
async def get_transactions(requestor=Depends(validate_jwt_token)):
    pipeline = [
        {
            "$lookup": {
                "from": "AccountInfo",
                "localField": "accountId",
                "foreignField": "id",
                "as": "account"
            }
        },
        {
            "$unwind": "$account"
        },
        {
            "$lookup": {
                "from": "Organization",
                "localField": "account.orgId",
                "foreignField": "id",
                "as": "account.organization"
            }
        },
        {
            "$unwind": "$account.organization"
        },
        {
            "$match": {
                "account.organization.id": requestor.orgId
            }
        },
        {
            "$lookup": {
                "from": "Currency",
                "localField": "account.organization.defaultCurrencyId",
                "foreignField": "id",
                "as": "account.organization.defaultCurrency"
            }
        },
        {
            "$unwind": "$account.organization.defaultCurrency"
        },
        {
            "$lookup": {
                "from": "Payment",
                "localField": "paymentId",
                "foreignField": "id",
                "as": "payment"
            }
        },
        {
            "$unwind": {
                "path": "$payment",
                "preserveNullAndEmptyArrays": True
            }

        },
        {
            "$lookup": {
                "from": "Currency",
                "localField": "payment.currencyId",
                "foreignField": "id",
                "as": "payment.currency"
            }
        },
        {
            "$unwind": {
                "path": "$payment.currency",
                "preserveNullAndEmptyArrays": True
            }

        },
        {
            "$lookup": {
                "from": "Expense",
                "localField": "expenseId",
                "foreignField": "id",
                "as": "expense"
            }
        },
        {
            "$unwind": {
                "path": "$expense",
                "preserveNullAndEmptyArrays": True
            }
        },
        {
            "$lookup": {
                "from": "Currency",
                "localField": "expense.currencyId",
                "foreignField": "id",
                "as": "expense.currency"
            }
        },
        {
            "$unwind": {
                "path": "$expense.currency",
                "preserveNullAndEmptyArrays": True
            }

        },
        {
            "$project": {
                "_id": 0
            }
        },
        {
            "$unset": ["account._id", "account.organization._id", "account.organization.defaultCurrency._id", "payment._id", "expense._id",
                       "payment.currency._id", "expense.currency._id"]
        },
        {
            "$sort": {
                "createdAt": -1
            }
        }
    ]

    transactions = DataAggregation("Transaction", pipeline)

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


@router.post("/transactions/payment/invoice", tags=["transactions"],
             dependencies=[Depends(JWTRequired), Depends(OrgAdminAccess)])
async def pay_invoice(payment_info: PayInvoice, requestor=Depends(validate_jwt_token)):
    # invoice = await prisma.invoice.find_unique(
    #     where={"id": payment_info.invoiceId},
    #     include={"workOrder": {"include": {"currency": True}}},
    # )

    pipeline = [
        {"$match": {"id": payment_info.invoiceId}},
        {
            "$lookup": {
                "from": "WorkOrder",
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
        },
        {
            "$project": {
                "_id": 0
            }
        },
        {
            "$unset": ["workOrder._id", "workOrder.currency._id"]
        }
    ]
    invoice = DataAggregation("Invoice", pipeline)
    payment_data = payment_info.dict()
    payment_data["currencyId"] = invoice.workOrder.currencyId
    del payment_data["accountId"]
    created_payment = PaymentInDb(**payment_data)
    DataWriter("Payment", created_payment)
    transaction = TransactionInDb(**{
                   "debit": 0,
                   "credit": created_payment.amount * created_payment.exchangeRate,
                   "paymentId": created_payment.id,
                   "accountId": payment_info.accountId,
               })
    DataWriter("Transaction", transaction.dict())
    return {"status": "transaction recorded"}


@router.post("/transactions/payment", tags=["transactions"],
             dependencies=[Depends(JWTRequired), Depends(OrgAdminAccess)])
async def record_payment(payment_info: Payment, requestor=Depends(validate_jwt_token)):
    payment_data = payment_info.dict()
    del payment_data["accountId"]

    payment_data = PaymentDB(**payment_data)
    DataWriter("Payment", payment_data.dict())
    transaction_data = Transaction(**({
                   "debit": 0,
                   "credit": payment_data.amount * payment_data.exchangeRate,
                   "paymentId": payment_data.id,
                   "accountId": payment_info.accountId,
               }))
    DataWriter("Transaction", transaction_data.dict())
    return {"status": "transaction recorded"}


@router.post("/transactions/expense", tags=["transactions"],
             dependencies=[Depends(JWTRequired), Depends(OrgAdminAccess)])
async def record_expense(expense_info: Payment, requestor=Depends(validate_jwt_token)):
    expense_data = expense_info.dict()
    del expense_data["accountId"]

    expense_data = ExpenseDB(**expense_data)

    DataWriter("Expense", expense_data.dict())
    transaction_data = Transaction(**({
                   "debit": expense_data.amount * expense_data.exchangeRate,
                   "credit": 0,
                   "expenseId": expense_data.id,
                   "accountId": expense_info.accountId,
               }))
    DataWriter("Transaction", transaction_data.dict())
    return {"status": "transaction recorded"}


@router.post("/transactions/record", tags=["transactions"],
             dependencies=[Depends(JWTRequired), Depends(OrgAdminAccess)])
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
        expense = ExpenseInDb(**data)
        DataWriter("Expense", data)
        t_id = expense.id
    else:
        payment = PaymentInDb(**data)
        DataWriter("Payment", payment)
        t_id = payment.id
    pdf_url = write_to_blob(
        path=f"invoices/{type.value}/{t_id}{extension}", data=content
    )

    if type == TransactionType.expense:
        expense = UpdateWriter("Expense", {"id": t_id}, {"docUrl": pdf_url})
    else:
        payment = UpdateWriter("Payment", {"id": t_id}, {"docUrl": pdf_url})
    account = SingleDataReader("Accounts", {"id": account_id})
    transaction = TransactionInDb(**{
        "debit": expense.amount * expense.exchangeRate if expense else 0,
        "credit": payment.amount * payment.exchangeRate if payment else 0,
        "expenseId": expense.id if expense else None,
        "paymentId": payment.id if payment else None,
        "accountId": account.id,
    })
    DataWriter("Transaction", transaction.dict())

    pipeline = [
        {"$match": {"id": transaction.id}},
        {
            "$lookup": {
                "from": "AccountInfo",
                "localField": "accountId",
                "foreignField": "id",
                "as": "account"
            }
        },
        {
            "$unwind": "$account"
        },
        {
            "$lookup": {
                "from": "Organization",
                "localField": "account.orgId",
                "foreignField": "id",
                "as": "account.organization"
            }
        },
        {
            "$unwind": "$account.organization"
        },
        {
            "$match": {
                "account.organization.id": requestor.orgId
            }
        },
        {
            "$lookup": {
                "from": "Currency",
                "localField": "account.organization.defaultCurrencyId",
                "foreignField": "id",
                "as": "account.organization.defaultCurrency"
            }
        },
        {
            "$unwind": "$account.organization.defaultCurrency"
        },
        {
            "$lookup": {
                "from": "Payment",
                "localField": "paymentId",
                "foreignField": "id",
                "as": "payment"
            }
        },
        {
            "$unwind": {
                "path": "$payment",
                "preserveNullAndEmptyArrays": True
            }

        },
        {
            "$lookup": {
                "from": "Currency",
                "localField": "payment.currencyId",
                "foreignField": "id",
                "as": "payment.currency"
            }
        },
        {
            "$unwind": {
                "path": "$payment.currency",
                "preserveNullAndEmptyArrays": True
            }

        },
        {
            "$lookup": {
                "from": "Expense",
                "localField": "expenseId",
                "foreignField": "id",
                "as": "expense"
            }
        },
        {
            "$unwind": {
                "path": "$expense",
                "preserveNullAndEmptyArrays": True
            }
        },
        {
            "$lookup": {
                "from": "Currency",
                "localField": "expense.currencyId",
                "foreignField": "id",
                "as": "expense.currency"
            }
        },
        {
            "$unwind": {
                "path": "$expense.currency",
                "preserveNullAndEmptyArrays": True
            }

        },
        {
            "$project": {
                "_id": 0
            }
        },
        {
            "$unset": ["account._id", "account.organization._id", "account.organization.defaultCurrency._id",
                       "payment._id", "expense._id",
                       "payment.currency._id", "expense.currency._id"]
        },
        {
            "$sort": {
                "createdAt": -1
            }
        }
    ]

    transaction = DataAggregation("Transaction", pipeline)[0]

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


@router.get("/transactions/document/{transaction_id}", tags=["transactions"],
            dependencies=[Depends(JWTRequired), Depends(OrgAdminAccess)])
async def download_document(transaction_id: str, requestor=Depends(validate_jwt_token)):

    pipeline = [
        {
            "$match": {
                "id": transaction_id
            }
        },
        {
            "$lookup": {
                "from": "AccountInfo",
                "localField": "accountId",
                "foreignField": "id",
                "as": "account"
            }
        },
        {
            "$unwind": "$account"
        },
        {
            "$lookup": {
                "from": "Organization",
                "localField": "account.orgId",
                "foreignField": "id",
                "as": "account.organization"
            }
        },
        {
            "$unwind": "$account.organization"
        },
        {
            "$match": {
                "account.organization.id": requestor.orgId
            }
        },
        {
            "$lookup": {
                "from": "Currency",
                "localField": "account.organization.defaultCurrencyId",
                "foreignField": "id",
                "as": "account.organization.defaultCurrency"
            }
        },
        {
            "$unwind": "$account.organization.defaultCurrency"
        },
        {
            "$lookup": {
                "from": "Payment",
                "localField": "paymentId",
                "foreignField": "id",
                "as": "payment"
            }
        },
        {
            "$unwind": {
                "path": "$payment",
                "preserveNullAndEmptyArrays": True
            }

        },
        {
            "$lookup": {
                "from": "Currency",
                "localField": "payment.currencyId",
                "foreignField": "id",
                "as": "payment.currency"
            }
        },
        {
            "$unwind": {
                "path": "$payment.currency",
                "preserveNullAndEmptyArrays": True
            }

        },
        {
            "$lookup": {
                "from": "Expense",
                "localField": "expenseId",
                "foreignField": "id",
                "as": "expense"
            }
        },
        {
            "$unwind": {
                "path": "$expense",
                "preserveNullAndEmptyArrays": True
            }
        },
        {
            "$lookup": {
                "from": "Currency",
                "localField": "expense.currencyId",
                "foreignField": "id",
                "as": "expense.currency"
            }
        },
        {
            "$unwind": {
                "path": "$expense.currency",
                "preserveNullAndEmptyArrays": True
            }

        },
        {
            "$project": {
                "_id": 0
            }
        },
        {
            "$unset": ["account._id", "account.organization._id", "account.organization.defaultCurrency._id",
                       "payment._id", "expense._id",
                       "payment.currency._id", "expense.currency._id"]
        },
        {
            "$sort": {
                "createdAt": -1
            }
        }
    ]

    transaction = DataAggregation("Transaction", pipeline)
    if not transaction:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST, detail="Transaction not found"
        )

    transaction = transaction[0]

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
