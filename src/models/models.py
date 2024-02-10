from datetime import datetime

from src.utils.auth import get_utc_timestamp

from typing import Optional
from uuid import uuid4
from pydantic import BaseModel, Field, validator


# class Gender(Enum):
#     male
#     female

# class WorkOrderType(Enum):
#     hourly
#     fixed

class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4().hex))
    orgId: Optional[str]
    email: str
    password: Optional[str]
    name: Optional[str]
    thumbURL: Optional[str]
    photoURL: Optional[str]
    birthDay: Optional[datetime]
    gender: Optional[str]
    phone: Optional[str]
    email_verified: Optional[bool]
    phone_verified: Optional[bool]
    active: bool
    superUser: bool
    staffUser: bool
    createdAt: int = Field(default_factory=get_utc_timestamp)
    updatedAt: int = Field(default_factory=get_utc_timestamp)


class UserRoles(BaseModel):
    id: str
    is_active: bool
    role_name: str


class UserAssignedRole(BaseModel):
    id: str
    userId: str
    userRoleId: str


class Organization(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4().hex))
    name: str
    abr: str
    registration: str
    defaultCurrencyId: str
    addressLine1: str
    addressLine2: str
    addressLine3: Optional[str]
    city: str
    country: str
    zip: str
    active: bool = False
    createdAt: int = Field(default_factory=get_utc_timestamp)
    updatedAt: Optional[int] = Field(default_factory=get_utc_timestamp)


class Client(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4().hex))
    orgId: str
    name: str
    abr: str
    registration: str
    domestic: bool = False
    internal: bool = False
    contact_name: str
    contact_email: str
    contact_phone: str
    addressLine1: str
    addressLine2: str
    addressLine3: Optional[str]
    city: str
    country: str
    zip: str
    active: bool = False
    createdAt: int = Field(default_factory=get_utc_timestamp)
    updatedAt: Optional[int] = Field(default_factory=get_utc_timestamp)


class WorkOrder(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4().hex))
    description: str
    clientId: str
    type: str
    rate: float
    currencyId: str
    startDate: int
    endDate: int
    docUrl: Optional[str]
    createdAt: int = Field(default_factory=get_utc_timestamp)
    updatedAt: int = Field(default_factory=get_utc_timestamp)


class Timesheet(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4().hex))
    description: str
    startTime: int
    endTime: int
    invoiced: bool = False
    invoiceId: Optional[str]
    workOrderId: str
    createdAt: int = Field(default_factory=get_utc_timestamp)
    updatedAt: int = Field(default_factory=get_utc_timestamp)
    chargedById: Optional[str]


class Invoice(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4().hex))
    invoice_number: str
    workOrderId: str
    currencyId: str
    invoicePeriodStart: int
    invoicePeriodEnd: int
    generatedOn: int
    dueBy: int
    paidOn: int
    docUrl: Optional[str]
    amount: float
    tax: Optional[float] = 0
    createdAt: int = Field(default_factory=get_utc_timestamp)
    updatedAt: int = Field(default_factory=get_utc_timestamp)


class InvoiceItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4().hex))
    invoiceId: str
    description: str
    quantity: str
    rate: float
    amount: float
    createdAt: int = Field(default_factory=get_utc_timestamp)
    updatedAt: int = Field(default_factory=get_utc_timestamp)


class Payment(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4().hex))
    invoiceId: Optional[str]
    currencyId: str
    exchangeRate: Optional[float] = 1
    description: str
    docUrl: Optional[str]
    amount: float
    createdAt: int = Field(default_factory=get_utc_timestamp)
    updatedAt: int = Field(default_factory=get_utc_timestamp)


class Expense(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4().hex))
    currencyId: str
    exchangeRate: Optional[float] = 1
    description: str
    docUrl: Optional[str]
    amount: float
    createdAt: int = Field(default_factory=get_utc_timestamp)
    updatedAt: int = Field(default_factory=get_utc_timestamp)


class Transaction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4().hex))
    debit: float
    credit: float
    paymentId: Optional[str]
    expenseId: Optional[str]
    accountId: Optional[str]
    createdAt: int = Field(default_factory=get_utc_timestamp)
    updatedAt: int = Field(default_factory=get_utc_timestamp)


class AccountInfoDB(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4().hex))
    orgId: str
    accountName: str
    accountNumber: str
    createdAt: int = Field(default_factory=get_utc_timestamp)
    updatedAt: int = Field(default_factory=get_utc_timestamp)


class CurrencyDb(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4().hex))
    name: str
    abr: str
    symbol: str
    createdAt: int = Field(default_factory=get_utc_timestamp)
    updatedAt: int = Field(default_factory=get_utc_timestamp)
