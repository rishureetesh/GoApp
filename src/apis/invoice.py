from functools import reduce
import pandas as pd
import io
import os
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query, Response, File, Form, UploadFile

from pydantic import BaseModel
from typing import List, Optional

from starlette.exceptions import HTTPException
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND
from src.config.database import CountDocuments, DataAggregation, DataWriter, DeleteData, SingleDataReader, UpdateWriter
from src.models.scalar import TransactionType
# from src.prisma import prisma
from src.config.settings import GST_PCT, TEMPLATE_ENV
from src.models.scalar import WorkOrderType
from src.utils.permissions import validate_jwt_token
from src.utils.convertors import get_base64_string
from src.utils.communication import send_invoice
from src.utils.pdf_generation import generate_invoice_pdf
from src.utils.storage import write_to_blob, read_blob, delete_blob

router = APIRouter()


class InvoiceDetails(BaseModel):
    work_order_id: str
    start_date: datetime
    end_date: datetime


class CreateInvoiceItem(BaseModel):
    description: str
    quantity: str
    rate: float
    amount: float


class CreateInvoice(BaseModel):
    workOrderId: str
    invoicePeriodStart: datetime
    invoicePeriodEnd: datetime
    generatedOn: Optional[datetime]
    dueBy: Optional[datetime]
    items: List[CreateInvoiceItem]
    amount: float
    tax: float
    include_time_charges: bool = False


class ShareInvoice(BaseModel):
    to_list: List[str]
    cc_list: List[str]


@router.get("/invoice", tags=["invoice"])
async def get_all_invoices(requestor=Depends(validate_jwt_token)):
    # return await prisma.invoice.find_many(
    #     where={"workOrder": {"client": {"organization": {"id": requestor.orgId}}}},
    #     include={
    #         "items": True,
    #         "payments": True,
    #         "workOrder": {
    #             "include": {
    #                 "client": {
    #                     "include": {
    #                         "organization": {
    #                             "include": {"accounts": True, "defaultCurrency": True}
    #                         }
    #                     }
    #                 },
    #                 "currency": True,
    #             }
    #         },
    #         "currency": True,
    #     },
    #     order={"createdAt": "desc"},
    # )
    
    pipeline = [
            {
                "$match": {
                    "workOrder.client.organization.id": requestor.orgId
                }
            },
            {
                "$lookup": {
                    "from": "workorders",
                    "localField": "workOrder.id",
                    "foreignField": "id",
                    "as": "workOrder"
                }
            },
            {
                "$unwind": "$workOrder"
            },
            {
                "$lookup": {
                    "from": "clients",
                    "localField": "workOrder.client.id",
                    "foreignField": "id",
                    "as": "workOrder.client"
                }
            },
            {
                "$unwind": "$workOrder.client"
            },
            {
                "$lookup": {
                    "from": "organizations",
                    "localField": "workOrder.client.organization.id",
                    "foreignField": "id",
                    "as": "workOrder.client.organization"
                }
            },
            {
                "$unwind": "$workOrder.client.organization"
            },
            {
                "$lookup": {
                    "from": "currencies",
                    "localField": "workOrder.currency.id",
                    "foreignField": "id",
                    "as": "workOrder.currency"
                }
            },
            {
                "$unwind": "$workOrder.currency"
            },
            {
                "$lookup": {
                    "from": "currencies",
                    "localField": "currency.id",
                    "foreignField": "id",
                    "as": "currency"
                }
            },
            {
                "$unwind": "$currency"
            },
            {
                "$lookup": {
                    "from": "items",
                    "localField": "items.id",
                    "foreignField": "id",
                    "as": "items"
                }
            },
            {
                "$lookup": {
                    "from": "payments",
                    "localField": "payments.id",
                    "foreignField": "id",
                    "as": "payments"
                }
            },
            {
                "$sort": {
                    "createdAt": -1
                }
            }
        ]
    return DataAggregation("Invoice", pipeline)


@router.get("/invoice/{invoice_id}", tags=["invoice"])
async def get_invoice(invoice_id: str, requestor=Depends(validate_jwt_token)):
    # invoice = await prisma.invoice.find_unique(
    #     where={"id": invoice_id},
    #     include={
    #         "items": True,
    #         "payments": True,
    #         "workOrder": {"include": {"client": True, "currency": True}},
    #     },
    # )
    
    pipeline = [
            {
                "$match": {
                    "id": invoice_id
                }
            },
            {
                "$lookup": {
                    "from": "Items",
                    "localField": "items.id",
                    "foreignField": "id",
                    "as": "items"
                }
            },
            {
                "$lookup": {
                    "from": "Payments",
                    "localField": "payments.id",
                    "foreignField": "id",
                    "as": "payments"
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
            {
                "$lookup": {
                    "from": "Clients",
                    "localField": "workOrder.client.id",
                    "foreignField": "id",
                    "as": "workOrder.client"
                }
            },
            {
                "$lookup": {
                    "from": "currencies",
                    "localField": "workOrder.currency.id",
                    "foreignField": "id",
                    "as": "workOrder.currency"
                }
            }
        ]
    
    invoice = DataAggregation("Invoice", pipeline)
    if not invoice:
        raise HTTPException(
            detail="Invalid Invoice ID", status_code=HTTP_400_BAD_REQUEST
        )
    return invoice


@router.get("/invoice/search", tags=["invoice"])
async def search_invoices(
    text_to_search: str = Query(..., min_length=3, max_length=50),
    requestor=Depends(validate_jwt_token)
):
    # invoices = await prisma.invoice.find_many(
    #     where={"invoice_number": {"contains": text_to_search}},
    #     include={
    #         "items": True,
    #         "payments": True,
    #         "workOrder": {"include": {"client": True, "currency": True}},
    #     },
    # )
    
    pipeline = [
            {
                "$match": {
                    "invoice_number": {"$regex": text_to_search, "$options": "i"}
                }
            },
            {
                "$lookup": {
                    "from": "Items",
                    "localField": "items.id",
                    "foreignField": "id",
                    "as": "items"
                }
            },
            {
                "$lookup": {
                    "from": "Payments",
                    "localField": "payments.id",
                    "foreignField": "id",
                    "as": "payments"
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
            {
                "$lookup": {
                    "from": "Clients",
                    "localField": "workOrder.client.id",
                    "foreignField": "id",
                    "as": "workOrder.client"
                }
            },
            {
                "$lookup": {
                    "from": "Currencies",
                    "localField": "workOrder.currency.id",
                    "foreignField": "id",
                    "as": "workOrder.currency"
                }
            }
        ]
    invoices = DataAggregation("Invoice", pipeline)
    return invoices


@router.delete("/invoice/{invoice_id}", tags=["invoice"])
async def delete_invoice(invoice_id: str, requestor=Depends(validate_jwt_token)):
    # invoice = await prisma.invoice.find_unique(where={"id": invoice_id})
    invoice = SingleDataReader("Invoice", {"id": invoice_id})
    if not invoice:
        raise HTTPException(
            detail="Invalid Invoice ID", status_code=HTTP_400_BAD_REQUEST
        )

    # await prisma.invoice.delete(where={"id": invoice_id})
    DeleteData("Invoice", {"id": invoice_id})
    return {"status": "acknowledged"}


@router.post("/invoice/generate/items", tags=["invoice"])
async def get_invoice_items(
    invoice_details: InvoiceDetails, requestor=Depends(validate_jwt_token)
):
    if invoice_details.start_date > invoice_details.end_date:
        raise HTTPException(
            detail="The start date cannot be greater than end date",
            status_code=HTTP_400_BAD_REQUEST,
        )
    # work_order = await prisma.workorder.find_unique(
    #     where={"id": invoice_details.work_order_id}, include={"client": True}
    # )
    
    pipeline = [
            {
                "$match": {
                    "id": invoice_details.work_order_id
                }
            },
            {
                "$lookup": {
                    "from": "Clients",
                    "localField": "client.id",
                    "foreignField": "id",
                    "as": "client"
                }
            },
            {
                "$unwind": "$client"
            }
        ]
    work_order = DataAggregation("WorkOrder", pipeline)
    if not work_order:
        raise HTTPException(
            detail="Invalid WorkOrder", status_code=HTTP_400_BAD_REQUEST
        )

    if invoice_details.end_date < work_order.startDate:
        raise HTTPException(
            detail="Invalid Invoice period. Falls outside the WorkOrder Duration",
            status_code=HTTP_400_BAD_REQUEST,
        )
    elif invoice_details.start_date > work_order.endDate:
        raise HTTPException(
            detail="Invalid Invoice period. Falls outside the WorkOrder Duration",
            status_code=HTTP_400_BAD_REQUEST,
        )

    start_date = invoice_details.start_date.date()
    end_date = invoice_details.end_date.date()
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())

    # time_charged = await prisma.timesheet.find_many(
    #     where={
    #         "startTime": {"gte": start_datetime, "lte": end_datetime},
    #         "invoiced": False,
    #     }
    # )
    
    pipeline = [
            {
                "$match": {
                    "startTime": {"$gte": start_datetime, "$lte": end_datetime},
                    "invoiced": False
                }
            }
        ]
    time_charged = DataAggregation("Timesheet", pipeline)
    if len(time_charged) == 0:
        raise HTTPException(
            detail="No time charged for the given period",
            status_code=HTTP_400_BAD_REQUEST,
        )
    charge_df = pd.DataFrame(
        list(
            map(
                lambda row: {
                    "description": row.description,
                    "startTime": row.startTime,
                    "endTime": row.endTime,
                },
                time_charged,
            )
        )
    )
    charge_df["duration"] = charge_df.apply(
        lambda row: round(
            float((row.endTime - row.startTime).total_seconds() / 3600), 2
        ),
        axis=1,
    )
    charge_df = charge_df[["description", "duration"]]
    grouped = charge_df.groupby(by="description").sum().reset_index()
    rate = (
        work_order.rate
        if work_order.type == WorkOrderType.hourly.value
        else work_order.rate / grouped.shape[0]
    )
    invoice_items = []
    for _, data in grouped.iterrows():
        qty = (
            round(data.duration, 2)
            if work_order.type == WorkOrderType.hourly.value
            else 1
        )
        quantity = f"{qty} hrs" if work_order.type == "hourly" else str(qty)
        invoice_items.append(
            {
                "description": data.description,
                "quantity": quantity,
                "rate": rate,
                "amount": rate * qty,
            }
        )
    return {
        "workOrderId": invoice_details.work_order_id,
        "invoicePeriodStart": start_datetime.isoformat(),
        "invoicePeriodEnd": end_datetime.isoformat(),
        "generatedOn": datetime.combine(
            datetime.now(), datetime.min.time()
        ).isoformat(),
        "dueBy": datetime.combine(
            (datetime.now() + timedelta(days=7)), datetime.max.time()
        ).isoformat(),
        "items": invoice_items,
        "tax": GST_PCT if work_order.client.domestic else 0,
        "amount": round(
            reduce(lambda total, item: total + item["amount"], invoice_items, 0), 2
        ),
    }


@router.post("/invoice", tags=["invoice"])
async def generate_invoice(
    invoice: CreateInvoice, requestor=Depends(validate_jwt_token)
):
    # work_order = await prisma.workorder.find_unique(
    #     where={"id": invoice.workOrderId},
    #     include={"currency": True, "client": {"include": {"organization": True}}},
    # )
    pipeline = [
            {
                "$match": {
                    "id": invoice.workOrderId
                }
            },
            {
                "$lookup": {
                    "from": "Currencies",
                    "localField": "currency.id",
                    "foreignField": "id",
                    "as": "currency"
                }
            },
            {
                "$lookup": {
                    "from": "Clients",
                    "localField": "client.id",
                    "foreignField": "id",
                    "as": "client"
                }
            },
            {
                "$lookup": {
                    "from": "Organizations",
                    "localField": "client.organization.id",
                    "foreignField": "id",
                    "as": "client.organization"
                }
            }
        ]
    
    work_order = DataAggregation("WorkOrder", pipeline)
    if not work_order:
        raise HTTPException(
            detail="Invalid WorkOrder", status_code=HTTP_400_BAD_REQUEST
        )
    timesheets = []
    if invoice.include_time_charges:
        # timesheets = await prisma.timesheet.find_many(
        #     where={
        #         "workOrderId": work_order.id,
        #         "startTime": {
        #             "gte": invoice.invoicePeriodStart,
        #             "lte": invoice.invoicePeriodEnd,
        #         },
        #         "invoiced": False,
        #     }
        # )
        
        pipeline = [
            {
                "$match": {
                    "workOrderId": work_order.id,
                    "startTime": {
                        "$gte": invoice.invoicePeriodStart,
                        "$lte": invoice.invoicePeriodEnd
                    },
                    "invoiced": False
                }
            }
        ]
        timesheets = DataAggregation("Timesheet", pipeline)
        if len(timesheets) == 0:
            raise HTTPException(
                detail="No time charged for the given period",
                status_code=HTTP_400_BAD_REQUEST,
            )
    total_amount = round(
        reduce(lambda amount, inv_det: amount + inv_det.amount, invoice.items, 0),
        2,
    )

    tax_amount = (
        round(((invoice.tax / 100) * total_amount), 2)
        if work_order.client.domestic
        else 0
    )
    invoice.generatedOn = (
        invoice.generatedOn
        if invoice.generatedOn
        else datetime.combine(datetime.now(), datetime.min.time())
    )
    invoice.dueBy = (
        invoice.dueBy
        if invoice.dueBy
        else datetime.combine((datetime.now() + timedelta(days=7)), datetime.max.time())
    )

    # invoice_number = await prisma.invoice.count()
    invoice_number = CountDocuments("Invoice")
    # created_invoice = await prisma.invoice.create(
    #     data={
    #         "workOrderId": work_order.id,
    #         "invoicePeriodStart": invoice.invoicePeriodStart,
    #         "invoicePeriodEnd": invoice.invoicePeriodEnd,
    #         "generatedOn": invoice.generatedOn,
    #         "dueBy": invoice.dueBy,
    #         "amount": total_amount,
    #         "tax": round(((invoice.tax / 100) * total_amount), 2)
    #         if work_order.client.domestic
    #         else 0,
    #         "invoice_number": f"{work_order.client.organization.abr}/{work_order.client.abr}/{datetime.strftime(datetime.now(), '%y%m%d')}/{invoice_number + 1}",
    #         "currencyId": work_order.currency.id,
    #     }
    # )
    
    created_invoice = DataWriter("Invoice",
            {
                "workOrderId": work_order.id,
                "invoicePeriodStart": invoice.invoicePeriodStart,
                "invoicePeriodEnd": invoice.invoicePeriodEnd,
                "generatedOn": invoice.generatedOn,
                "dueBy": invoice.dueBy,
                "amount": total_amount,
                "tax": round(((invoice.tax / 100) * total_amount), 2)
                if work_order.client.domestic
                else 0,
                "invoice_number": f"{work_order.client.organization.abr}/{work_order.client.abr}/{datetime.strftime(datetime.now(), '%y%m%d')}/{invoice_number + 1}",
                "currencyId": work_order.currency.id,
            }
        )

    # await prisma.invoiceitem.create_many(
    #     data=list(
    #         map(
    #             lambda item: {
    #                 "invoiceId": created_invoice.id,
    #                 "description": item.description,
    #                 "quantity": item.quantity,
    #                 "rate": item.rate,
    #                 "amount": item.amount,
    #             },
    #             invoice.items,
    #         )
    #     )
    # )
    
    DataWriter("InvoiceItem",
            list(
                map(
                    lambda item: {
                        "invoiceId": created_invoice.id,
                        "description": item.description,
                        "quantity": item.quantity,
                        "rate": item.rate,
                        "amount": item.amount,
                    },
                    invoice.items,
                )
            ),
            True    
    )
    # created_invoice = await prisma.invoice.find_unique(
    #     where={"id": created_invoice.id},
    #     include={
    #         "items": True,
    #         "currency": True,
    #         "workOrder": {
    #             "include": {
    #                 "currency": True,
    #                 "client": {"include": {"organization": True}},
    #             }
    #         },
    #         "payments": True,
    #     },
    # )
    
    pipeline = [
            {
                "$match": {
                    "id": created_invoice.id
                }
            },
            {
                "$lookup": {
                    "from": "Items",
                    "localField": "id",
                    "foreignField": "invoiceId",
                    "as": "items"
                }
            },
            {
                "$lookup": {
                    "from": "WorkOrders",
                    "localField": "workOrderId",
                    "foreignField": "id",
                    "as": "workOrder"
                }
            },
            {
                "$lookup": {
                    "from": "Currencies",
                    "localField": "currencyId",
                    "foreignField": "id",
                    "as": "currency"
                }
            },
            {
                "$lookup": {
                    "from": "Clients",
                    "localField": "workOrder.clientId",
                    "foreignField": "id",
                    "as": "client"
                }
            },
            {
                "$lookup": {
                    "from": "Organizations",
                    "localField": "client.organizationId",
                    "foreignField": "id",
                    "as": "organization"
                }
            },
            {
                "$lookup": {
                    "from": "Payments",
                    "localField": "id",
                    "foreignField": "invoiceId",
                    "as": "payments"
                }
            }
        ]
    
    created_invoice = DataAggregation("Invoice", pipeline)

    pdf_options = {
        "page-size": "A4",
        "margin-top": "0.05in",
        "margin-right": "0.05in",
        "margin-bottom": "0.3in",
        "margin-left": "0.05in",
        "encoding": "UTF-8",
        "footer-left": "#[page]",
        "footer-right": f"Generated on: {created_invoice.createdAt.strftime('%d/%m/%Y %H:%M:%S +00:00/UTC')}",
        "footer-font-size": "8",
    }

    pdf = generate_invoice_pdf(
        invoice_data=created_invoice.dict(),
        pdf_options=pdf_options,
        template="templates/invoice.html",
    )
    pdf_url = write_to_blob(
        path=f"invoices/{created_invoice.invoice_number}.pdf", data=pdf
    )
    if not pdf_url:
        # await prisma.invoice.delete(where={"id": created_invoice.id})
        DeleteData("Invoice", {"id": created_invoice.id})
        raise HTTPException(
            detail="Error generating invoice", status_code=HTTP_400_BAD_REQUEST
        )
    # await prisma.invoice.update(
    #     where={"id": created_invoice.id},
    #     data={"docUrl": f"invoices/{created_invoice.invoice_number}.pdf"},
    # )
    UpdateWriter(
        "Invoice",
        {"id": created_invoice.id},
        {"docUrl": f"invoices/{created_invoice.invoice_number}.pdf"}
    )
    if invoice.include_time_charges:
        # await prisma.timesheet.update_many(
        #     where={"id": {"in": list(map(lambda ts: ts.id, timesheets))}},
        #     data={
        #         "invoiced": True,
        #         "invoiceId": created_invoice.id,
        #     },
        # )
        UpdateWriter("Timesheet",
            {"_id": {"$in": list(map(lambda ts: ts["_id"], timesheets))}},
            {"$set": {"invoiced": True, "invoiceId": created_invoice.id}}
        )
    return Response(pdf, status_code=200, media_type="application/pdf")


@router.get("/invoice/document/{invoice_id}", tags=["invoice"])
async def get_invoice_document(invoice_id: str, requestor=Depends(validate_jwt_token)):
    # invoice = await prisma.invoice.find_unique(
    #     where={"id": invoice_id},
    # )
    invoice = SingleDataReader("Invoice", {"id": invoice_id})
    if not invoice:
        raise HTTPException(detail="Invalid Invoice", status_code=HTTP_400_BAD_REQUEST)
    if not invoice.docUrl:
        raise HTTPException(
            detail="Invoice document not found", status_code=HTTP_404_NOT_FOUND
        )
    doc = read_blob(path=invoice.docUrl)
    return Response(
        doc,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={invoice_id}.pdf"},
    )


@router.get("/invoice/cancel/{invoice_id}", tags=["invoice"])
async def cancel_invoice(invoice_id: str, requestor=Depends(validate_jwt_token)):
    # invoice = await prisma.invoice.find_unique(
    #     where={"id": invoice_id},
    #     include={
    #         "items": True,
    #         "currency": True,
    #         "workOrder": {
    #             "include": {
    #                 "currency": True,
    #                 "client": {"include": {"organization": True}},
    #             }
    #         },
    #         "payments": True,
    #     },
    # )
    
    pipeline = [
            {
                "$match": {
                    "id": invoice_id
                }
            },
            {
                "$lookup": {
                    "from": "items",
                    "localField": "id",
                    "foreignField": "invoiceId",
                    "as": "items"
                }
            },
            {
                "$lookup": {
                    "from": "currencies",
                    "localField": "currencyId",
                    "foreignField": "id",
                    "as": "currency"
                }
            },
            {
                "$lookup": {
                    "from": "workOrders",
                    "localField": "workOrderId",
                    "foreignField": "id",
                    "as": "workOrder"
                }
            },
            {
                "$lookup": {
                    "from": "currencies",
                    "localField": "workOrder.currencyId",
                    "foreignField": "id",
                    "as": "workOrder.currency"
                }
            },
            {
                "$lookup": {
                    "from": "clients",
                    "localField": "workOrder.clientId",
                    "foreignField": "id",
                    "as": "workOrder.client"
                }
            },
            {
                "$lookup": {
                    "from": "organizations",
                    "localField": "workOrder.client.organizationId",
                    "foreignField": "id",
                    "as": "workOrder.client.organization"
                }
            },
            {
                "$lookup": {
                    "from": "payments",
                    "localField": "id",
                    "foreignField": "invoiceId",
                    "as": "payments"
                }
            }
        ]
    
    invoice = DataAggregation("Invoice", pipeline)
    if not invoice:
        raise HTTPException(detail="Invalid Invoice", status_code=HTTP_400_BAD_REQUEST)
    if not invoice.docUrl:
        raise HTTPException(
            detail="Invoice document not found", status_code=HTTP_404_NOT_FOUND
        )

    pdf_options = {
        "page-size": "A4",
        "margin-top": "0.05in",
        "margin-right": "0.05in",
        "margin-bottom": "0.3in",
        "margin-left": "0.05in",
        "encoding": "UTF-8",
        "footer-left": "#[page]",
        "footer-right": f"Generated on: {invoice.createdAt.strftime('%d/%m/%Y %H:%M:%S +00:00/UTC')}",
        "footer-font-size": "8",
    }
    invoice_data = invoice.dict()
    invoice_data["dueBy"] = None
    pdf = generate_invoice_pdf(
        invoice_data=invoice_data,
        pdf_options=pdf_options,
        template="templates/invoice.html",
    )
    delete_blob(path=invoice.docUrl)
    write_to_blob(path=f"invoices/{invoice.invoice_number}.pdf", data=pdf)
    # await prisma.invoice.update(
    #     where={"id": invoice_id},
    #     data={"dueBy": None},
    # )
    UpdateWriter("Invoice", {"id": invoice_id}, {"dueBy": None})
    return Response(
        pdf,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={invoice_id}.pdf"},
    )


@router.post("/invoice/pay/{invoice_id}", tags=["invoice"])
async def pay_invoice(
    invoice_id: str,
    document: UploadFile = File(..., description="transaction document"),
    exchange_rate: float = Form(..., description="Exchange Rate of the currency"),
    account_id: str = Form(..., description="Account Id"),
    requestor=Depends(validate_jwt_token)
):
    # invoice = await prisma.invoice.find_unique(
    #     where={"id": invoice_id},
    #     include={
    #         "items": True,
    #         "currency": True,
    #         "workOrder": {
    #             "include": {
    #                 "currency": True,
    #                 "client": {"include": {"organization": True}},
    #             }
    #         },
    #         "payments": True,
    #     },
    # )
    pipeline = [
            {
                "$match": {
                    "id": invoice_id
                }
            },
            {
                "$lookup": {
                    "from": "items",
                    "localField": "id",
                    "foreignField": "invoiceId",
                    "as": "items"
                }
            },
            {
                "$lookup": {
                    "from": "currencies",
                    "localField": "currencyId",
                    "foreignField": "id",
                    "as": "currency"
                }
            },
            {
                "$lookup": {
                    "from": "workOrders",
                    "localField": "workOrderId",
                    "foreignField": "id",
                    "as": "workOrder"
                }
            },
            {
                "$lookup": {
                    "from": "currencies",
                    "localField": "workOrder.currencyId",
                    "foreignField": "id",
                    "as": "workOrder.currency"
                }
            },
            {
                "$lookup": {
                    "from": "clients",
                    "localField": "workOrder.clientId",
                    "foreignField": "id",
                    "as": "workOrder.client"
                }
            },
            {
                "$lookup": {
                    "from": "organizations",
                    "localField": "workOrder.client.organizationId",
                    "foreignField": "id",
                    "as": "workOrder.client.organization"
                }
            },
            {
                "$lookup": {
                    "from": "payments",
                    "localField": "id",
                    "foreignField": "invoiceId",
                    "as": "payments"
                }
            }
        ]
    invoice = DataAggregation("Invoice", pipeline)
    if not invoice:
        raise HTTPException(detail="Invalid Invoice", status_code=HTTP_400_BAD_REQUEST)

    if invoice.paidOn:
        raise HTTPException(
            detail="Invoice already paid", status_code=HTTP_400_BAD_REQUEST
        )

    if not invoice.dueBy:
        raise HTTPException(
            detail="Invoice is cancelled and cannot be paid",
            status_code=HTTP_400_BAD_REQUEST,
        )

    content = io.BytesIO(document.file.read())
    extension = os.path.splitext(document.filename)[1]

    # payment = await prisma.payment.create(
    #     data={
    #         "description": f"payment for invoice {invoice.invoice_number}",
    #         "amount": invoice.amount + invoice.tax,
    #         "currencyId": invoice.workOrder.currencyId,
    #         "exchangeRate": exchange_rate,
    #         "invoiceId": invoice.id,
    #     }
    # )
    DataWriter(
        "Payment",
        {
            "description": f"payment for invoice {invoice.invoice_number}",
            "amount": invoice.amount + invoice.tax,
            "currencyId": invoice.workOrder.currencyId,
            "exchangeRate": exchange_rate,
            "invoiceId": invoice.id,
        }
    )
    pdf_url = write_to_blob(
        path=f"invoices/{TransactionType.payment.value}/{payment.id}{extension}",
        data=content,
    )
    # payment = await prisma.payment.update(
    #     where={"id": payment.id}, data={"docUrl": pdf_url}
    # )
    payment = UpdateWriter(
        "Payment",
        {"id": payment.id},
        {"docUrl": pdf_url}
    )
    # account = await prisma.accountinfo.find_unique(where={"id": account_id})
    account = SingleDataReader("AccountInfo", {"id": account_id})
    # await prisma.transaction.create(
    #     data={
    #         "debit": 0,
    #         "credit": payment.amount * payment.exchangeRate,
    #         "paymentId": payment.id if payment else None,
    #         "accountId": account.id,
    #     }
    # )
    
    DataWriter(
        "Transaction",
        {
            "debit": 0,
            "credit": payment.amount * payment.exchangeRate,
            "paymentId": payment.id if payment else None,
            "accountId": account.id,
        }
    )
    
    # invoice = await prisma.invoice.update(
    #     where={"id": invoice_id},
    #     data={
    #         "paidOn": datetime.now(),
    #     },
    #     include={
    #         "items": True,
    #         "currency": True,
    #         "workOrder": {
    #             "include": {
    #                 "currency": True,
    #                 "client": {"include": {"organization": True}},
    #             }
    #         },
    #         "payments": True,
    #     },
    # )
    
    pipeline = [
            {
                "$match": {
                    "id": invoice_id
                }
            },
            {
                "$lookup": {
                    "from": "items",
                    "localField": "id",
                    "foreignField": "invoiceId",
                    "as": "items"
                }
            },
            {
                "$lookup": {
                    "from": "currencies",
                    "localField": "currencyId",
                    "foreignField": "id",
                    "as": "currency"
                }
            },
            {
                "$lookup": {
                    "from": "workOrders",
                    "localField": "workOrderId",
                    "foreignField": "id",
                    "as": "workOrder"
                }
            },
            {
                "$lookup": {
                    "from": "currencies",
                    "localField": "workOrder.currencyId",
                    "foreignField": "id",
                    "as": "workOrder.currency"
                }
            },
            {
                "$lookup": {
                    "from": "clients",
                    "localField": "workOrder.clientId",
                    "foreignField": "id",
                    "as": "workOrder.client"
                }
            },
            {
                "$lookup": {
                    "from": "organizations",
                    "localField": "workOrder.client.organizationId",
                    "foreignField": "id",
                    "as": "workOrder.client.organization"
                }
            },
            {
                "$lookup": {
                    "from": "payments",
                    "localField": "id",
                    "foreignField": "invoiceId",
                    "as": "payments"
                }
            }
        ]
    invoice = DataAggregation("Invoice", pipeline)
    
    pdf_options = {
        "page-size": "A4",
        "margin-top": "0.05in",
        "margin-right": "0.05in",
        "margin-bottom": "0.3in",
        "margin-left": "0.05in",
        "encoding": "UTF-8",
        "footer-left": "#[page]",
        "footer-right": f"Generated on: {invoice.createdAt.strftime('%d/%m/%Y %H:%M:%S +00:00/UTC')}",
        "footer-font-size": "8",
    }
    invoice_data = invoice.dict()
    pdf = generate_invoice_pdf(
        invoice_data=invoice_data,
        pdf_options=pdf_options,
        template="templates/invoice.html",
    )
    delete_blob(path=invoice.docUrl)
    write_to_blob(path=f"invoices/{invoice.invoice_number}.pdf", data=pdf)
    return Response(
        pdf,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={invoice_id}.pdf"},
    )


@router.post("/invoice/share/{invoice_id}", tags=["invoice"])
async def share_invoice(
    invoice_id: str,
    emails: ShareInvoice,
    requestor=Depends(validate_jwt_token)
):
    # invoice = await prisma.invoice.find_unique(
    #     where={"id": invoice_id},
    #     include={
    #         "items": True,
    #         "currency": True,
    #         "workOrder": {
    #             "include": {
    #                 "currency": True,
    #                 "client": {"include": {"organization": True}},
    #             }
    #         },
    #         "payments": True,
    #     },
    # )
    
    pipeline = [
            {
                "$match": {
                    "id": invoice_id
                }
            },
            {
                "$lookup": {
                    "from": "items",
                    "localField": "id",
                    "foreignField": "invoiceId",
                    "as": "items"
                }
            },
            {
                "$lookup": {
                    "from": "currencies",
                    "localField": "currencyId",
                    "foreignField": "id",
                    "as": "currency"
                }
            },
            {
                "$lookup": {
                    "from": "workOrders",
                    "localField": "workOrderId",
                    "foreignField": "id",
                    "as": "workOrder"
                }
            },
            {
                "$lookup": {
                    "from": "currencies",
                    "localField": "workOrder.currencyId",
                    "foreignField": "id",
                    "as": "workOrder.currency"
                }
            },
            {
                "$lookup": {
                    "from": "clients",
                    "localField": "workOrder.clientId",
                    "foreignField": "id",
                    "as": "workOrder.client"
                }
            },
            {
                "$lookup": {
                    "from": "organizations",
                    "localField": "workOrder.client.organizationId",
                    "foreignField": "id",
                    "as": "workOrder.client.organization"
                }
            },
            {
                "$lookup": {
                    "from": "payments",
                    "localField": "id",
                    "foreignField": "invoiceId",
                    "as": "payments"
                }
            }
        ]
    invoice = DataAggregation("Invoice", pipeline)
    if not invoice:
        raise HTTPException(detail="Invalid Invoice", status_code=HTTP_400_BAD_REQUEST)
    if not invoice.docUrl:
        raise HTTPException(
            detail="Invoice document not found", status_code=HTTP_404_NOT_FOUND
        )
    pdf = read_blob(path=invoice.docUrl)
    invoice_data = invoice.dict()
    invoice_status = "CANCELLED"
    if invoice.paidOn:
        invoice_status = "PAID"
    elif invoice.dueBy:
        invoice_status = "DUE"

    invoice_data["status"] = invoice_status
    invoice_data["total"] = invoice.amount + invoice.tax
    invoice_data["requestor"] = requestor.dict()

    if invoice.workOrder.client.contact_email not in emails.to_list:
        emails.to_list.append(invoice.workOrder.client.contact_email)
    if requestor.email not in emails.cc_list:
        emails.cc_list.append(requestor.email)

    mail_response = await send_invoice(
        to_list=emails.to_list,
        cc_list=emails.cc_list,
        report=pdf,
        template_data=invoice_data,
    )

    if mail_response:
        return {"message": "Invoice shared successfully"}
    else:
        raise HTTPException(
            detail="Failed to share invoice", status_code=HTTP_400_BAD_REQUEST
        )
