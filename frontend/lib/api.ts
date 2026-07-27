const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
export const ORGANIZATION_ID = process.env.NEXT_PUBLIC_ORGANIZATION_ID ?? "00000000-0000-0000-0000-000000000001";

export type AuthenticatedUser = {
  id: string;
  organization_id: string;
  email: string;
  name: string;
  role: "admin" | "operator" | "viewer";
};

export type ResourceType = "raw_material" | "packaging" | "product" | "mix";
export type UnitType = "g" | "kg" | "ml" | "unit";

export type Resource = {
  id: string;
  organization_id: string;
  code: string;
  name: string;
  type: ResourceType;
  unit: UnitType;
  minimum_stock: string;
  active: boolean;
  latest_unit_cost: string | null;
  latest_supplier_name: string | null;
};

export type ResourceStock = {
  resource_id: string;
  code: string;
  name: string;
  type: ResourceType;
  unit: UnitType;
  quantity: string;
};

export type FormulaSummary = {
  id: string;
  organization_id: string;
  product_resource_id: string | null;
  name: string;
  version: number;
  status: "draft" | "active" | "archived";
  active_version: boolean;
};

export type FormulaDetail = FormulaSummary & {
  notes: string | null;
  items: Array<{
    ingredient_resource_id: string;
    ingredient_name: string;
    percentage: string;
    sort_order: number;
  }>;
};

export type DashboardSummary = {
  resources_count: number;
  formulas_count: number;
  production_batches_count: number;
  low_stock_count: number;
  imported_sales_count: number;
  imported_sales_total: string;
  imported_expenses_count: number;
  imported_expenses_total: string;
  sales_channels_count: number;
  expense_categories_count: number;
  system_sales_count: number;
  system_sales_total: string;
  cancelled_system_sales_count: number;
  system_expenses_count: number;
  system_expenses_total: string;
  cancelled_system_expenses_count: number;
  month_expenses_total: string;
  year_expenses_total: string;
  expenses_count: number;
  top_expense_category_name: string | null;
  top_expense_category_total: string;
  sales_same_period_total: string;
  confirmed_purchases_count: number;
  confirmed_purchases_total: string;
  draft_purchases_count: number;
  cancelled_purchases_count: number;
  finished_products_stock_total: string;
};

export type DashboardActivityItem = {
  id: string;
  date: string;
  type: string;
  description: string;
  value: string | null;
  href: string | null;
};

export type SaleOption = {
  id: string;
  name: string;
};

export type SaleOptions = {
  channels: SaleOption[];
  payment_methods: SaleOption[];
  points_of_sale: SaleOption[];
};

export type ProductForSale = {
  id: string;
  code: string;
  name: string;
  unit: string;
  available_stock: string;
  suggested_price: string | null;
  price_list_name: string | null;
};

export type SaleLineRead = {
  id: string;
  product_resource_id: string;
  product_name: string;
  quantity: string;
  unit_price: string;
  discount: string;
  line_total: string;
};

export type SaleRead = {
  id: string;
  code: string;
  sale_date: string;
  channel_id: string | null;
  channel_name: string | null;
  point_of_sale_id: string | null;
  point_of_sale_name: string | null;
  customer_name: string | null;
  payment_method_id: string | null;
  payment_method_name: string | null;
  status: "draft" | "confirmed" | "cancelled" | "imported";
  subtotal: string;
  discount_total: string;
  total: string;
  notes: string | null;
  source: "system" | "imported";
  quantity_total: string;
  products_summary: string;
  lines: SaleLineRead[];
  movements: Array<{
    id: string;
    resource_id: string;
    resource_name: string;
    type: string;
    quantity: string;
    occurred_at: string;
  }>;
};

export type SearchResult = {
  id: string;
  type: string;
  title: string;
  subtitle: string;
  href: string;
};

export type PurchaseRead = {
  id: string;
  code: string;
  purchase_date: string;
  supplier_name: string;
  receipt_number: string | null;
  status: "draft" | "confirmed" | "cancelled";
  subtotal: string;
  total: string;
  notes: string | null;
  confirmed_at: string | null;
  cancelled_at: string | null;
  cancellation_reason: string | null;
  lines: Array<{
    id: string;
    resource_id: string;
    resource_name: string;
    quantity: string;
    unit: UnitType;
    unit_price: string;
    line_total: string;
  }>;
  movements: Array<{
    id: string;
    resource_id: string;
    resource_name: string;
    type: string;
    quantity: string;
    unit_cost_snapshot: string | null;
    occurred_at: string;
  }>;
};

export type PurchaseOptions = {
  suppliers: Array<{
    id: string;
    name: string;
  }>;
};

export type ExpenseOption = {
  id: string;
  name: string;
};

export type ExpenseOptions = {
  categories: ExpenseOption[];
  payment_methods: ExpenseOption[];
  suppliers: string[];
};

export type ExpenseRead = {
  id: string;
  expense_date: string;
  category_id: string | null;
  category_name: string;
  description: string;
  amount: string;
  payment_method_id: string | null;
  payment_method_name: string | null;
  supplier_name: string | null;
  receipt_number: string | null;
  notes: string | null;
  status: "confirmed" | "cancelled";
  origin: "system" | "imported";
  source_label: string | null;
  cancelled_at: string | null;
  cancellation_reason: string | null;
  editable: boolean;
  cancellable: boolean;
};

export type ExpenseListResponse = {
  items: ExpenseRead[];
  total: string;
  count: number;
};

export type ExpenseSummary = {
  month_total: string;
  year_total: string;
  count: number;
  top_category_name: string | null;
  top_category_total: string;
  sales_same_period_total: string;
};

export type InventoryMovementRead = {
  id: string;
  occurred_at: string;
  type: string;
  resource_name: string;
  resource_code: string;
  quantity: string;
  unit: UnitType;
  reason: string | null;
  origin: string;
  document_label: string | null;
};

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    cache: "no-store",
    credentials: "include",
  });

  if (!response.ok) {
    const error = await response.json().catch(() => null);
    const detail = error?.detail;
    const message =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail.map((item) => item.msg ?? JSON.stringify(item)).join(" ")
          : detail
            ? JSON.stringify(detail)
            : `No se pudo obtener la informacion solicitada. Codigo ${response.status}.`;
    throw new Error(message);
  }

  return response.json();
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => null);
    const detail = error?.detail;
    const message =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail.map((item) => item.msg ?? JSON.stringify(item)).join(" ")
          : detail
            ? JSON.stringify(detail)
            : `API error ${response.status}`;
    throw new Error(message);
  }

  return response.json();
}

export async function apiPut<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "PUT",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => null);
    const detail = error?.detail;
    const message =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail.map((item) => item.msg ?? JSON.stringify(item)).join(" ")
          : detail
            ? JSON.stringify(detail)
            : `API error ${response.status}`;
    throw new Error(message);
  }

  return response.json();
}
