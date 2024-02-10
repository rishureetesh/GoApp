from enum import Enum


class Gender(Enum):
    Male = "male"
    Female = "female"


class WorkOrderType(Enum):
    hourly = "hourly"
    fixed = "fixed"


class TransactionType(Enum):
    expense = "expense"
    payment = "payment"
