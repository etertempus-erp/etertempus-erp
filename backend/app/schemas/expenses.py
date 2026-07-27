from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class ExpenseOption(BaseModel):
    id: UUID
    name: str


class ExpenseOptions(BaseModel):
    categories: list[ExpenseOption]
    payment_methods: list[ExpenseOption]
    suppliers: list[str]


class ExpenseCreate(BaseModel):
    organization_id: UUID
    expense_date: date
    category_id: UUID
    description: str = Field(min_length=2, max_length=220)
    amount: Decimal = Field(gt=0)
    payment_method_id: UUID
    supplier_name: str | None = Field(default=None, max_length=180)
    receipt_number: str | None = Field(default=None, max_length=120)
    notes: str | None = None


class ExpenseUpdate(BaseModel):
    organization_id: UUID
    supplier_name: str | None = Field(default=None, max_length=180)
    receipt_number: str | None = Field(default=None, max_length=120)
    notes: str | None = None


class ExpenseCancel(BaseModel):
    organization_id: UUID
    reason: str = Field(min_length=3, max_length=240)


class ExpenseRead(BaseModel):
    id: UUID
    expense_date: date
    category_id: UUID | None = None
    category_name: str
    description: str
    amount: Decimal
    payment_method_id: UUID | None = None
    payment_method_name: str | None = None
    supplier_name: str | None = None
    receipt_number: str | None = None
    notes: str | None = None
    status: str
    origin: str
    source_label: str | None = None
    cancelled_at: datetime | None = None
    cancellation_reason: str | None = None
    editable: bool
    cancellable: bool


class ExpenseListResponse(BaseModel):
    items: list[ExpenseRead]
    total: Decimal
    count: int


class ExpenseSummary(BaseModel):
    month_total: Decimal
    year_total: Decimal
    count: int
    top_category_name: str | None = None
    top_category_total: Decimal
    sales_same_period_total: Decimal
