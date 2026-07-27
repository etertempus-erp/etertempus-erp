from decimal import Decimal

from pydantic import BaseModel


class DashboardActivityItem(BaseModel):
    id: str
    date: str
    type: str
    description: str
    value: str | None = None
    href: str | None = None


class DashboardSummary(BaseModel):
    resources_count: int
    formulas_count: int
    production_batches_count: int
    low_stock_count: int
    imported_sales_count: int
    imported_sales_total: Decimal
    imported_expenses_count: int
    imported_expenses_total: Decimal
    sales_channels_count: int
    expense_categories_count: int
    system_sales_count: int
    system_sales_total: Decimal
    cancelled_system_sales_count: int
    system_expenses_count: int
    system_expenses_total: Decimal
    cancelled_system_expenses_count: int
    month_expenses_total: Decimal
    year_expenses_total: Decimal
    expenses_count: int
    top_expense_category_name: str | None = None
    top_expense_category_total: Decimal
    sales_same_period_total: Decimal
    confirmed_purchases_count: int
    confirmed_purchases_total: Decimal
    draft_purchases_count: int
    cancelled_purchases_count: int
    finished_products_stock_total: Decimal
