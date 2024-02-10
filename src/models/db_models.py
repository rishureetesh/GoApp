from pydantic import BaseModel

from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from src.models.scalar import Gender, WorkOrderType


class CollectionName:
    UsersBase = 'goapp_users'
    UsersRoles = 'goapp_user_Roles'
    UserPermissions = 'goapp_user_permissions'

    UserAssignedRole = 'goapp_user_assigned_role'
    UserAssignedAdditionalPermission = 'goapp_user_assigned_additional_permission'

    RolesAssociatedWithPermissions = 'goapp_role_assigned_permissions'


def WrapperNone(args):
    return '' if args is None else args


class UsersBase(BaseModel):
    user_slug: str
    first_name: str
    last_name: str
    email: str
    date_created: int
    is_active: bool = True
    is_deleted: bool = False


class UserWithPassword(UsersBase):
    password: str


class UserAssignedRole(BaseModel):
    uar_slug: str
    user_role_slug: str
    date_assigned: str
    is_active: bool


class UserAssignedAdditionalPermission(BaseModel):
    uaar_slug: str
    user_perm_slug: str
    date_assigned: str
    is_active: bool


class UserRoles(BaseModel):
    role_slug: str
    is_active: bool
    role_name: str


class UserPermissions(BaseModel):
    perm_slug: str
    is_active: bool
    perm_name: str


class RolesAssociatedWithPermissions(BaseModel):
    rawp_slug: str
    role_slug: str
    perm_slug: str
    is_active: bool


##################################################

class DbModel(BaseModel):
    id: str
    createdAt: int
    updatedAt: int


class UserBase(BaseModel):
    orgId: Optional[str]
    email: str
    name: str
    thumbURL: Optional[str]
    photoURL: Optional[str]
    birthDay: Optional[str]
    gender: str
    phone: str
    email_verified: bool = False
    phone_verified: bool = False
    active: bool = False
    superUser: bool = False
    staffUser: bool = False


class UserInDb(DbModel, UserBase):
    password: str


#########################################################

class OrganizationBase(BaseModel):
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


class OrganizationInDb(DbModel, OrganizationBase):
    pass


#########################################################

class ClientBase(BaseModel):
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


class ClientInDb(DbModel, ClientBase):
    pass


#########################################################

class WorkOrderBase(BaseModel):
    description: str
    clientId: str
    type: WorkOrderType = 'hourly'
    rate: float
    currencyId: str
    startDate: datetime
    endDate: datetime
    docUrl: Optional[str]


class WorkOrderInDb(DbModel, WorkOrderBase):
    pass


#########################################################

class TimesheetBase(BaseModel):
    description: str
    startTime: datetime
    endTime: datetime
    workOrderId: str


class TimesheetInDb(DbModel, TimesheetBase):
    pass


#########################################################

class InvoiceBase(BaseModel):
    invoice_number: str
    workOrderId: datetime
    invoicePeriodStart: datetime
    invoicePeriodEnd: datetime
    generatedOn: datetime
    dueBy: datetime
    paidOn: datetime
    docUrl: Optional[str]
    amount: float
    tax: float


class InvoiceInDb(DbModel, InvoiceBase):
    pass


class InvoiceItemBase(BaseModel):
    invoiceId: str
    description: str
    quantity: str
    rate: float
    amount: float


class InvoiceItemInDb(DbModel, BaseModel):
    pass


#########################################################

class PaymentBase(BaseModel):
    invoiceId: Optional[str]
    currencyId: str
    exchangeRate: float = 1.0000
    description: str
    docUrl: Optional[str]
    amount: float


class PaymentInDb(DbModel, PaymentBase):
    pass


class ExpenseBase(BaseModel):
    currencyId: str
    exchangeRate: float = 1.0000
    description: str
    docUrl: Optional[str]
    amount: float


class ExpenseInDb(DbModel, PaymentBase):
    pass


class TransactionBase(BaseModel):
    credit: float = 0
    debit: float = 0
    paymentId: Optional[str]
    expenseId: Optional[str]
    accountId: str


class TransactionInDb(DbModel, TransactionBase):
    pass


#########################################################

class AccountInfoBase(BaseModel):
    orgId: str
    accountName: str
    accountNumber: str


class AccountInfoInDb(DbModel, AccountInfoBase):
    pass


class CurrencyBase(BaseModel):
    name: str
    abr: str
    symbol: str


class CurrencyInDb(DbModel, CurrencyBase):
    pass
