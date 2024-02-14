import io
import os
from datetime import datetime, timedelta
from typing import List, Optional

import pandas as pd
from fastapi import APIRouter, Depends, File, Form, UploadFile, Response, Query
from pydantic import BaseModel
from starlette.exceptions import HTTPException
from starlette.status import HTTP_400_BAD_REQUEST

from src.config.database import DataAggregation, DataWriter, DeleteData, MultiDataReader, SingleDataReader, UpdateWriter
from src.config.settings import CUT_OFF_DATE
from src.models.models import WorkOrder, TimesheetDB
from src.models.scalar import WorkOrderType
from src.utils.communication import send_timesheet
from src.utils.date_time import format_seconds_to_hr_mm
from src.utils.permissions import validate_jwt_token, OrgAdminAccess, JWTRequired, OrgStaffAccess
from src.utils.storage import write_to_blob, delete_blob, read_blob
from src.utils.timesheet import generate_timesheet_calendar

router = APIRouter()


class CreateWorkOrder(BaseModel):
    description: str
    clientId: str
    type: WorkOrderType
    rate: float
    currencyId: str
    startDate: datetime
    endDate: datetime
    docUrl: Optional[str]


class UpdateWorkOrder(BaseModel):
    description: Optional[str]
    clientId: Optional[str]
    type: Optional[WorkOrderType]
    rate: Optional[float]
    currencyId: Optional[str]
    startDate: Optional[datetime]
    endDate: Optional[datetime]
    docUrl: Optional[str]


class Timesheet(BaseModel):
    description: str
    startTime: datetime
    endTime: datetime


class UpdateTimesheet(BaseModel):
    description: Optional[str]


class TimeCharge(BaseModel):
    start: datetime
    end: datetime
    work_order_id: str


class TimeChargeMail(BaseModel):
    start: datetime
    end: datetime
    work_order_id: str
    to: List[str]
    cc: List[str]


@router.get("/workOrder", tags=["work_orders"], dependencies=[Depends(JWTRequired), Depends(OrgStaffAccess)])
async def read_work_orders(requestor=Depends(validate_jwt_token)):
    pipeline = [
        {
            "$lookup": {
                "from": "Client",
                "localField": "clientId",
                "foreignField": "id",
                "as": "client"
            }
        },
        {
            "$unwind": "$client"
        },
        {
            "$lookup": {
                "from": "Organization",
                "localField": "client.orgId",
                "foreignField": "id",
                "as": "client.organization"
            }
        },
        {
            "$unwind": "$client.organization"
        },
        {
            "$lookup": {
                "from": "Invoice",
                "localField": "id",
                "foreignField": "workOrderId",
                "as": "invoices"
            }
        },
        {
            "$unwind": {
                "path": "$invoices",
                "preserveNullAndEmptyArrays": True
            }
        },
        {
            "$lookup": {
                "from": "Timesheet",
                "localField": "id",
                "foreignField": "workOrderId",
                "as": "changeability"
            }
        },
        {
            "$lookup": {
                "from": "Currency",
                "localField": "currencyId",
                "foreignField": "id",
                "as": "currency"
            }
        },
        {
            "$unwind": "$currency"
        },
        {
            "$project": {
                "_id": 0
            }
        },
        {
            "$unset": ["currency._id", "invoices._id", "changeability._id", "client.organization._id", "client._id"]
        }
    ]
    return DataAggregation("WorkOrder", pipeline)


@router.post("/workOrder", tags=["work_orders"], dependencies=[Depends(JWTRequired), Depends(OrgAdminAccess)])
async def create_work_order(
        document: UploadFile = File(..., description="WorkOrder Contract"),
        description: str = Form(..., description="Work order Description"),
        clientId: str = Form(..., description="Client Id"),
        type: WorkOrderType = Form(..., description="Work Order Type"),
        rate: float = Form(..., description="Work Order Rate"),
        currencyId: str = Form(..., description="Currency Id"),
        startDate: datetime = Form(..., description="Start Date"),
        endDate: datetime = Form(..., description="End Date"),
        requestor=Depends(validate_jwt_token)
):
    work_order = CreateWorkOrder(
        description=description,
        clientId=clientId,
        type=type,
        rate=rate,
        currencyId=currencyId,
        startDate=startDate,
        endDate=endDate,
    )

    content: bytes = io.BytesIO(document.file.read())
    extension = os.path.splitext(document.filename)[1]
    client = SingleDataReader("Client", {"id": work_order.clientId})
    if not client:
        raise HTTPException(
            detail="Invalid client id",
            status_code=HTTP_400_BAD_REQUEST,
        )
    data = work_order.dict()
    data["type"] = data["type"].value

    created_work_order = WorkOrder(**data)
    DataWriter("WorkOrder", created_work_order.dict())
    uploaded_path = write_to_blob(
        data=content, path=f"work-orders/{created_work_order.id}{extension}"
    )
    if uploaded_path:
        UpdateWriter("WorkOrder", {"id": created_work_order.id}, {"docUrl": uploaded_path})

    pipeline = [
        {"$match": {"id": created_work_order.id}},
        {
            "$lookup": {
                "from": "Client",
                "localField": "clientId",
                "foreignField": "id",
                "as": "client"
            }
        },
        {
            "$unwind": "$client"
        },
        {
            "$lookup": {
                "from": "Organization",
                "localField": "client.orgId",
                "foreignField": "id",
                "as": "client.organization"
            }
        },
        {
            "$unwind": "$client.organization"
        },
        {
            "$lookup": {
                "from": "Currency",
                "localField": "currencyId",
                "foreignField": "id",
                "as": "currency"
            }
        },
        {
            "$unwind": "$currency"
        },
        {
            "$project": {
                "_id": 0
            }
        },
        {
            "$unset": ["client._id", "client.organization._id", "currency._id"]
        }
    ]
    created_work_order = DataAggregation("WorkOrder", pipeline)
    return created_work_order[0]


@router.get("/workOrder/{work_order_id}", tags=["work_orders"],
            dependencies=[Depends(JWTRequired), Depends(OrgStaffAccess)])
async def read_work_order(work_order_id: str, requestor=Depends(validate_jwt_token)):
    pipeline = [
        {"$match": {"id": work_order_id}},
        {
            "$lookup": {
                "from": "Invoice",
                "localField": "id",
                "foreignField": "workOrderId",
                "as": "invoices"
            }
        },
        {
            "$lookup": {
                "from": "Timesheet",
                "localField": "workOrderId",
                "foreignField": "id",
                "as": "changeability"
            }
        },
        {
            "$lookup": {
                "from": "Currency",
                "localField": "currencyId",
                "foreignField": "id",
                "as": "currency"
            }
        },
        {
            "$lookup": {
                "from": "Client",
                "localField": "clientId",
                "foreignField": "id",
                "as": "client"
            }
        },
        {
            "$unwind":
                {
                    "path": "$client",
                    "preserveNullAndEmptyArrays": True
                }
        },
        {
            "$unwind":
                {
                    "path": "$currency",
                    "preserveNullAndEmptyArrays": True
                }
        },
        {
            "$unwind": {
                "path": "$changeability",
                "preserveNullAndEmptyArrays": True
            }
        },
        {
            "$unwind": {
                "path": "$invoices",
                "preserveNullAndEmptyArrays": True
            }
        },
        {
            "$project": {
                "_id": 0
            }
        },
        {
            "$unset": ["invoices._id", "changeability._id", "client._id", "currency._id"]
        }
    ]
    work_order = DataAggregation("WorkOrder", pipeline)
    if not work_order:
        raise HTTPException(
            detail="Invalid Work-Order id",
            status_code=HTTP_400_BAD_REQUEST,
        )
    return work_order[0]


@router.post("/workOrder/{work_order_id}", tags=["work_orders"],
             dependencies=[Depends(JWTRequired), Depends(OrgAdminAccess)])
async def update_work_order(
        work_order_id: str,
        update_info: UpdateWorkOrder,
        requestor=Depends(validate_jwt_token)
):
    work_order = SingleDataReader("WorkOrder", {"id": work_order_id})
    if not work_order:
        raise HTTPException(
            detail="Invalid Work-Order id",
            status_code=HTTP_400_BAD_REQUEST,
        )

    work_order = WorkOrder(**work_order)

    if update_info.clientId and update_info.clientId != work_order.clientId:
        client = SingleDataReader("Client", {"id": update_info.clientId})
        if not client:
            raise HTTPException(
                detail="Invalid Client id",
                status_code=HTTP_400_BAD_REQUEST,
            )

    if update_info.currencyId and update_info.currencyId != work_order.currencyId:
        currency = SingleDataReader("Currency", {"id": update_info.currencyId})
        if not currency:
            raise HTTPException(
                detail="Invalid currency id",
                status_code=HTTP_400_BAD_REQUEST,
            )

    if update_info.startDate and update_info.endDate:
        if update_info.startDate > update_info.endDate:
            raise HTTPException(
                detail="Work order start date cannot be after it ends",
                status_code=HTTP_400_BAD_REQUEST,
            )
    elif update_info.startDate:
        if update_info.startDate > work_order.endDate:
            raise HTTPException(
                detail="Work order start date cannot be after it ends",
                status_code=HTTP_400_BAD_REQUEST,
            )
    elif update_info.endDate:
        if work_order.startDate > update_info.endDate:
            raise HTTPException(
                detail="Work order start date cannot be after it ends",
                status_code=HTTP_400_BAD_REQUEST,
            )

    update_info.description = (
        update_info.description if update_info.description else work_order.description
    )
    update_info.clientId = (
        update_info.clientId if update_info.clientId else work_order.clientId
    )
    update_info.type = update_info.type.value if update_info.type else work_order.type
    update_info.rate = update_info.rate if update_info.rate else work_order.rate
    update_info.currencyId = (
        update_info.currencyId if update_info.currencyId else work_order.currencyId
    )
    update_info.startDate = (
        update_info.startDate if update_info.startDate else work_order.startDate
    )
    update_info.endDate = (
        update_info.endDate if update_info.endDate else work_order.endDate
    )
    update_info.docUrl = update_info.docUrl if update_info.docUrl else work_order.docUrl

    UpdateWriter(
        "WorkOrder", {"id": work_order_id}, update_info.dict()
    )

    pipeline = [
        {"$match": {"id": work_order_id}},
        {
            "$lookup": {
                "from": "Client",
                "localField": "clientId",
                "foreignField": "id",
                "as": "client"
            }
        },
        {
            "$unwind": "$client"
        },
        {
            "$lookup": {
                "from": "Organization",
                "localField": "client.orgId",
                "foreignField": "id",
                "as": "client.organization"
            }
        },
        {
            "$unwind": "$client.organization"
        },
        {
            "$lookup": {
                "from": "Invoice",
                "localField": "id",
                "foreignField": "workOrderId",
                "as": "invoices"
            }
        },
        {
            "$unwind": {
                "path": "$invoices",
                "preserveNullAndEmptyArrays": True
            }
        },
        {
            "$lookup": {
                "from": "Timesheet",
                "localField": "id",
                "foreignField": "workOrderId",
                "as": "changeability"
            }
        },
        {
            "$lookup": {
                "from": "Currency",
                "localField": "currencyId",
                "foreignField": "id",
                "as": "currency"
            }
        },
        {
            "$unwind": "$currency"
        },
        {
            "$project": {
                "_id": 0
            }
        },
        {
            "$unset": ["currency._id", "invoices._id", "changeability._id", "client.organization._id", "client._id"]
        }
    ]

    updated_work_order = DataAggregation("WorkOrder", pipeline)

    return updated_work_order[0]


@router.delete("/workOrder/{work_order_id}", tags=["work_orders"],
               dependencies=[Depends(JWTRequired), Depends(OrgAdminAccess)])
async def delete_work_order(
        work_order_id: str,
        requestor=Depends(validate_jwt_token)
):
    work_order = SingleDataReader("WorkOrder", {"id": work_order_id})
    if not work_order:
        raise HTTPException(
            detail="Invalid Work-Order id",
            status_code=HTTP_400_BAD_REQUEST,
        )
    work_order = WorkOrder(**work_order)
    if work_order.docUrl:
        uploaded_file_name = work_order.docUrl.split("/")[-1]
        delete_blob(path=f"work-orders/{uploaded_file_name}")
    DeleteData("WorkOrder", {"id": work_order_id})
    return {"status": "acknowledged"}


@router.get("/workOrder/charge/{work_order_id}", tags=["work_orders"],
            dependencies=[Depends(JWTRequired), Depends(OrgStaffAccess)])
async def week_summary(
        work_order_id: str,
        start_date: Optional[datetime] = Query(None),
        end_date: Optional[datetime] = Query(None),
        requestor=Depends(validate_jwt_token)
):
    work_order = SingleDataReader("WorkOrder", {"id": work_order_id})
    if not work_order:
        raise HTTPException(
            detail="Invalid Work-Order id",
            status_code=HTTP_400_BAD_REQUEST,
        )
    timesheets = None
    work_order = WorkOrder(**work_order)
    if start_date and end_date:
        pipeline = [
            {
                "$match": {
                    "workOrderId": work_order_id,
                    "startTime": {"$gte": start_date},
                    "endTime": {"$lte": end_date},
                    "chargedById": requestor.id,
                }
            },
            {
                "$sort": {"startTime": 1}
            },
            {
                "$project": {
                    "_id": 0
                }
            }
        ]
        timesheets = DataAggregation("Timesheet", pipeline)
    elif start_date and not end_date:
        pipeline = [
            {
                "$match": {
                    "workOrderId": work_order_id,
                    "startTime": {"$gte": start_date}
                }
            },
            {
                "$project": {
                    "_id": 0
                }
            }
        ]
        timesheets = DataAggregation("Timesheet", pipeline)
    elif not start_date and end_date:
        pipeline = [
            {
                "$match": {
                    "workOrderId": work_order_id,
                    "endTime": {"$lte": end_date}
                }
            },
            {
                "$project": {
                    "_id": 0
                }
            }
        ]
        timesheets = DataAggregation("Timesheet", pipeline)
    else:
        timesheets = MultiDataReader("Timesheet", {"workOrderId": work_order_id})
    data = []
    total_duration = 0
    max_duration = 0
    if len(timesheets) > 0:
        df = pd.DataFrame(list(map(lambda x: x.dict(), timesheets)))
        df = df[["id", "description", "startTime", "endTime", "invoiced"]]
        df["duration"] = df["endTime"] - df["startTime"]
        df["date"] = df["startTime"].dt.date
        grouped_df = df.groupby("date")["duration"].sum().reset_index()
        total_duration = grouped_df["duration"].sum()
        max_duration = grouped_df["duration"].max()
        data = grouped_df.to_dict("records")
        for day in data:
            day_data = df[df["date"] == day["date"]]
            day_data["duration"] = day_data.apply(
                lambda x: format_seconds_to_hr_mm(x.duration.total_seconds()), axis=1
            )
            day["timesheets"] = day_data.to_dict("records")
    current_date = start_date
    while current_date <= end_date:
        date_to_search = current_date.date()
        if not any(day["date"] == date_to_search for day in data):
            data.append(
                {
                    "date": date_to_search,
                    "duration": "0:00 hrs",
                    "pct": 0,
                    "invoiced": date_to_search < work_order.startDate.date()
                                or date_to_search < CUT_OFF_DATE.date(),
                    "timesheets": [],
                }
            )
        else:
            day = next((day for day in data if day["date"] == date_to_search), None)
            day_duration = day["duration"]

            charge_df = df[df["date"] == date_to_search]
            invoiced_list = charge_df["invoiced"].tolist()
            day["invoiced"] = (
                    len(set(invoiced_list)) == 1 and list(set(invoiced_list))[0] == True
            )

            day["pct"] = round(
                (day["duration"].total_seconds() / max_duration.total_seconds()) * 100,
                0,
            )
            hours = int(day_duration.total_seconds() // 3600)
            minutes = int((day_duration.total_seconds() // 60) % 60)

            if minutes == 0:
                day["duration"] = f"{hours}:00 hrs"
            else:
                day["duration"] = f"{hours}:{minutes} hrs"
        current_date += timedelta(days=1)
    total_duration = total_duration if total_duration else timedelta(seconds=0)
    sorted_data = sorted(data, key=lambda x: x["date"])
    return {
        "total_duration": format_seconds_to_hr_mm(total_duration.total_seconds()),
        "total_duration_numeric": round(total_duration.total_seconds() / 3600, 2),
        "details": sorted_data,
    }


@router.get("/workOrder/statistics/{work_order_id}", tags=["work_orders"],
            dependencies=[Depends(JWTRequired), Depends(OrgStaffAccess)])
async def monthly_summary(
        work_order_id: str,
        date: datetime = Query(None),
        requestor=Depends(validate_jwt_token)
):
    work_order = SingleDataReader("WorkOrder", {"id": work_order_id})
    if not work_order:
        raise HTTPException(
            detail="Invalid Work-Order id",
            status_code=HTTP_400_BAD_REQUEST,
        )

    month, year = date.month, date.year

    start_of_month = datetime(year, month, 1)

    next_month = start_of_month.replace(day=28) + timedelta(days=4)
    end_of_month = next_month - timedelta(days=next_month.day)
    end_of_month = end_of_month.replace(hour=23, minute=59, second=59)
    current_date = start_of_month
    pipeline = [
        {
            "$match": {
                "workOrderId": work_order_id,
                "startTime": {"$gte": start_of_month, "$lte": end_of_month},
                "chargedById": requestor.id,
            }
        },
        {
            "$sort": {"startTime": 1}
        },
        {
            "$project": {
                "_id": 0
            }
        }
    ]

    time_charges = DataAggregation("Timesheet", pipeline)
    available_days = []
    total_invoiced_seconds = timedelta(seconds=0)
    total_charged_seconds = timedelta(seconds=0)
    if len(time_charges) > 0:
        df = pd.DataFrame(list(map(lambda x: x.dict(), time_charges)))
        df["date"] = df["startTime"].dt.date
        grouped_df = df.groupby("date")["id"].count().reset_index()
        available_days = grouped_df["date"].tolist()
        df["duration"] = df["endTime"] - df["startTime"]
        total_invoiced_seconds = df[df["invoiced"] == True]["duration"].sum()
        total_charged_seconds = df["duration"].sum()
    day_info = []
    while current_date <= end_of_month:
        if current_date.date() in available_days:
            charges = df[df["date"] == current_date.date()]
            invoiced_list = charges["invoiced"].tolist()
            day_is_invoiced = not False in invoiced_list
            day_is_charged = True
        else:
            day_is_invoiced = False
            day_is_charged = False

        day_info.append(
            {
                "date": current_date.isoformat(),
                "isInvoiced": day_is_invoiced,
                "isCharged": day_is_charged,
            }
        )

        current_date += timedelta(days=1)

    return {
        "detail": day_info,
        "invoiced": format_seconds_to_hr_mm(total_invoiced_seconds.total_seconds()),
        "charged": format_seconds_to_hr_mm(total_charged_seconds.total_seconds()),
    }


@router.post("/workOrder/charge/{work_order_id}", tags=["work_orders"],
             dependencies=[Depends(JWTRequired), Depends(OrgStaffAccess)])
async def charge_time(
        time_to_charge: Timesheet,
        work_order_id: str,
        requestor=Depends(validate_jwt_token)
):
    work_order = SingleDataReader("WorkOrder", {"id": work_order_id})
    if not work_order:
        raise HTTPException(
            detail="Invalid Work-Order id",
            status_code=HTTP_400_BAD_REQUEST,
        )

    if time_to_charge.startTime > time_to_charge.endTime:
        raise HTTPException(
            detail="Start Time Cannot be greater than the endTime",
            status_code=HTTP_400_BAD_REQUEST,
        )
    time_charge = time_to_charge.dict()
    time_charge["chargedById"] = requestor.id
    time_charge["workOrderId"] = work_order_id
    time_sheet = TimesheetDB(**time_charge)
    DataWriter("Timesheet", time_sheet.dict())
    return time_sheet


@router.post("/workOrder/charge/edit/{timesheet_id}", tags=["work_orders"],
             dependencies=[Depends(JWTRequired), Depends(OrgStaffAccess)])
async def update_charged_time(
        update_info: UpdateTimesheet,
        timesheet_id: str,
        requestor=Depends(validate_jwt_token)
):
    timesheet = SingleDataReader("Timesheet", {"id": timesheet_id})
    if not timesheet:
        raise HTTPException(
            detail="Invalid Timesheet id",
            status_code=HTTP_400_BAD_REQUEST,
        )
    timesheet = TimesheetDB(**timesheet)
    if update_info.description and update_info.description != timesheet.description:
        UpdateWriter("Timesheet", {"id": timesheet_id}, {"description": update_info.description})
        timesheet = SingleDataReader("Timesheet", {"id": timesheet_id})
        timesheet = TimesheetDB(**timesheet)

    return timesheet


@router.delete("/workOrder/charge/delete/{timesheet_id}", tags=["work_orders"],
               dependencies=[Depends(JWTRequired), Depends(OrgStaffAccess)])
async def delete_charged_time(
        timesheet_id: str,
        requestor=Depends(validate_jwt_token)
):
    timesheet = SingleDataReader("Timesheet", {"id": timesheet_id})
    if not timesheet:
        raise HTTPException(
            detail="Invalid Timesheet id",
            status_code=HTTP_400_BAD_REQUEST,
        )

    DeleteData("Timesheet", {"id": timesheet_id})

    return {"status": "acknowledged"}


@router.get("/workOrder/document/{work_order_id}", tags=["work_orders"],
            dependencies=[Depends(JWTRequired), Depends(OrgAdminAccess)])
async def download_work_order_document(
        work_order_id: str, requestor=Depends(validate_jwt_token)
):

    pipeline = [
        {"$match": {"id": work_order_id}},
        {
            "$lookup": {
                "from": "Invoice",
                "localField": "id",
                "foreignField": "workOrderId",
                "as": "invoices"
            }
        },
        {
            "$lookup": {
                "from": "Timesheet",
                "localField": "workOrderId",
                "foreignField": "id",
                "as": "changeability"
            }
        },
        {
            "$lookup": {
                "from": "Currency",
                "localField": "currencyId",
                "foreignField": "id",
                "as": "currency"
            }
        },
        {
            "$lookup": {
                "from": "Client",
                "localField": "clientId",
                "foreignField": "id",
                "as": "client"
            }
        },
        {
            "$unwind":
                {
                    "path": "$client",
                    "preserveNullAndEmptyArrays": True
                }
        },
        {
            "$unwind":
                {
                    "path": "$currency",
                    "preserveNullAndEmptyArrays": True
                }
        },
        {
            "$unwind": {
                "path": "$changeability",
                "preserveNullAndEmptyArrays": True
            }
        },
        {
            "$unwind": {
                "path": "$invoices",
                "preserveNullAndEmptyArrays": True
            }
        },
        {
            "$project": {
                "_id": 0
            }
        },
        {
            "$unset": ["invoices._id", "changeability._id", "client._id", "currency._id"]
        }
    ]

    work_order = DataAggregation("WorkOrder", pipeline)
    if not work_order:
        raise HTTPException(
            detail="Invalid Work-Order id",
            status_code=HTTP_400_BAD_REQUEST,
        )
    work_order = WorkOrder(**work_order[0])
    if not work_order.docUrl:
        raise HTTPException(
            detail="No Document Uploaded",
            status_code=HTTP_400_BAD_REQUEST,
        )
    uploaded_file_name = work_order.docUrl.split("/")[-1]
    doc = read_blob(path=f"work-orders/{uploaded_file_name}")

    return Response(
        doc,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={uploaded_file_name}"},
    )


@router.post("/workOrder/timesheet/report", tags=["work_orders"],
             dependencies=[Depends(JWTRequired), Depends(OrgAdminAccess)])
async def download_work_order_document(
        details: TimeCharge,
        requestor=Depends(validate_jwt_token)
):
    pipeline = [
        {"$match": {"id": details.work_order_id}},
        {
            "$lookup": {
                "from": "Client",
                "localField": "clientId",
                "foreignField": "id",
                "as": "client"
            }
        },
        {
            "$lookup": {
                "from": "Organization",
                "localField": "client.orgId",
                "foreignField": "id",
                "as": "client.organization"
            }
        },
        {
            "$unwind":
                {
                    "path": "$client",
                    "preserveNullAndEmptyArrays": True
                }
        },
        {
            "$unwind":
                {
                    "path": "$client.organization",
                    "preserveNullAndEmptyArrays": True
                }
        },
        {
            "$project": {
                "_id": 0
            }
        },
        {
            "$unset": ["client.organization._id", "client._id"]
        }
    ]
    work_order = DataAggregation("WorkOrder", pipeline)
    if not work_order:
        raise HTTPException(
            detail="Invalid Work-Order id",
            status_code=HTTP_400_BAD_REQUEST,
        )
    work_order = WorkOrder(**work_order[0])

    pipeline = [
        {
            "$match": {
                "workOrderId": work_order.id,
                "startTime": {"$gte": details.start},
                "endTime": {"$lte": details.end},
            }
        },
        {
            "$sort": {"startTime": 1}
        },
        {
            "$project": {
                "_id": 0
            }
        }
    ]

    time_charges = DataAggregation("Timesheet", pipeline)

    if len(time_charges) == 0:
        raise HTTPException(
            detail="No time charges found",
            status_code=HTTP_400_BAD_REQUEST,
        )

    _, report = generate_timesheet_calendar(time_charges, details, work_order)
    return Response(report, status_code=200, media_type="application/pdf")


@router.post("/workOrder/timesheet/send", tags=["work_orders"],
             dependencies=[Depends(JWTRequired), Depends(OrgAdminAccess)])
async def download_work_order_document(
        details: TimeChargeMail,
        requestor=Depends(validate_jwt_token)
):
    # work_order = await prisma.workorder.find_unique(
    #     where={"id": details.work_order_id},
    #     include={"client": {"include": {"organization": True}}},
    # )

    pipeline = [
        {"$match": {"id": details.work_order_id}},
        {
            "$lookup": {
                "from": "Clients",
                "localField": "clientId",
                "foreignField": "id",
                "as": "client"
            }
        },
        {
            "$lookup": {
                "from": "Organizations",
                "localField": "client.orgId",
                "foreignField": "id",
                "as": "client.organization"
            }
        },
        {
            "$unwind":
                {
                    "path": "$client",
                    "preserveNullAndEmptyArrays": True
                }
        },
        {
            "$unwind":
                {
                    "path": "$client.organization",
                    "preserveNullAndEmptyArrays": True
                }
        },
        {
            "$project": {
                "_id": 0
            }
        },
        {
            "$unset": ["client.organization._id", "client._id"]
        }
    ]
    work_order = DataAggregation("WorkOrder", pipeline)
    if not work_order:
        raise HTTPException(
            detail="Invalid Work-Order id",
            status_code=HTTP_400_BAD_REQUEST,
        )
    # time_charges = await prisma.timesheet.find_many(
    #     where={
    #         "workOrderId": work_order.id,
    #         "startTime": {"gte": details.start},
    #         "endTime": {"lte": details.end},
    #     },
    #     order={
    #         "startTime": "asc",
    #     },
    # )

    pipeline = [
        {
            "$match": {
                "workOrderId": work_order.id,
                "startTime": {"$gte": details.start},
                "endTime": {"$lte": details.end}
            }
        },
        {
            "$sort": {
                "startTime": 1
            }
        },
        {
            "$project": {
                "_id": 0
            }
        }
    ]

    time_charges = DataAggregation("Timesheet", pipeline)

    if len(time_charges) == 0:
        raise HTTPException(
            detail="No time charges found",
            status_code=HTTP_400_BAD_REQUEST,
        )

    total_hours, report = generate_timesheet_calendar(time_charges, details, work_order)
    data = {
        "requestor_name": requestor.name,
        "requestor_email": requestor.email,
        "start_date": datetime.strftime(details.start, "%Y-%m-%d"),
        "end_date": datetime.strftime(details.end, "%Y-%m-%d"),
        "billable_hours": total_hours,
        "org_name": work_order.client.organization.name,
    }

    cc_list = details.cc + [requestor.email]
    email = await send_timesheet(
        to_list=details.to, cc_list=cc_list, report=report, template_data=data
    )
    return Response(report, status_code=200, media_type="application/pdf")
