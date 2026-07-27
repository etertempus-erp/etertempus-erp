from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class SaleLineCreate(BaseModel):
    product_resource_id: UUID
    quantity: Decimal = Field(gt=0)
    unit_price: Decimal = Field(ge=0)
    discount: Decimal = Field(default=Decimal("0"), ge=0)


class SaleCreate(BaseModel):
    organization_id: UUID
    sale_date: date
    channel_id: UUID
    point_of_sale_id: UUID | None = None
    customer_name: str | None = Field(default=None, max_length=180)
    payment_method_id: UUID
    notes: str | None = None
    created_by: str | None = Field(default=None, max_length=120)
    lines: list[SaleLineCreate] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_lines(self):
        for line in self.lines:
            gross = line.quantity * line.unit_price
            if line.discount > gross:
                raise ValueError("El descuento no puede ser mayor que el subtotal de la linea.")
        return self


class SaleCancel(BaseModel):
    organization_id: UUID
    reason: str = Field(min_length=3, max_length=240)
    cancelled_by: str | None = Field(default=None, max_length=120)


class SaleLineRead(BaseModel):
    id: UUID
    product_resource_id: UUID
    product_name: str
    quantity: Decimal
    unit_price: Decimal
    discount: Decimal
    line_total: Decimal


class SaleMovementRead(BaseModel):
    id: UUID
    resource_id: UUID
    resource_name: str
    type: str
    quantity: Decimal
    occurred_at: datetime


class SaleRead(BaseModel):
    id: UUID
    code: str
    sale_date: date
    channel_id: UUID | None = None
    channel_name: str | None = None
    point_of_sale_id: UUID | None = None
    point_of_sale_name: str | None = None
    customer_name: str | None = None
    payment_method_id: UUID | None = None
    payment_method_name: str | None = None
    status: str
    subtotal: Decimal
    discount_total: Decimal
    total: Decimal
    notes: str | None = None
    source: str
    quantity_total: Decimal
    products_summary: str
    lines: list[SaleLineRead] = []
    movements: list[SaleMovementRead] = []


class SaleCreated(BaseModel):
    sale: SaleRead
    remaining_stock: dict[UUID, Decimal]


class SaleOption(BaseModel):
    id: UUID
    name: str


class SaleOptions(BaseModel):
    channels: list[SaleOption]
    payment_methods: list[SaleOption]
    points_of_sale: list[SaleOption]


class ProductForSale(BaseModel):
    id: UUID
    code: str
    name: str
    unit: str
    available_stock: Decimal
    suggested_price: Decimal | None = None
    price_list_name: str | None = None
