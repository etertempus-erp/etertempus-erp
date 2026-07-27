"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { Ban, Eye, Filter, Pencil, Plus, Zap } from "lucide-react";

import { AppShell } from "@/components/AppShell";
import {
  apiGet,
  apiPost,
  ExpenseListResponse,
  ExpenseOptions,
  ExpenseRead,
  ExpenseSummary,
  ORGANIZATION_ID,
} from "@/lib/api";
import { friendlyErrorMessage } from "@/lib/messages";

function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

function formatMoney(value: string | number) {
  return Number(value || 0).toLocaleString("es-UY", {
    maximumFractionDigits: 2,
    style: "currency",
    currency: "UYU",
  });
}

function formatDate(value: string) {
  const [year, month, day] = value.split("-");
  return year && month && day ? `${day}/${month}/${year}` : value;
}

function statusLabel(status: ExpenseRead["status"]) {
  return status === "cancelled" ? "Anulado" : "Confirmado";
}

function originLabel(origin: ExpenseRead["origin"]) {
  return origin === "imported" ? "Importado" : "ERP";
}

export default function ExpensesPage() {
  const [options, setOptions] = useState<ExpenseOptions | null>(null);
  const [summary, setSummary] = useState<ExpenseSummary | null>(null);
  const [data, setData] = useState<ExpenseListResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    date_from: "",
    date_to: "",
    category_id: "",
    payment_method_id: "",
    supplier: "",
    status: "",
    origin: "",
    q: "",
  });

  const queryString = useMemo(() => {
    const params = new URLSearchParams({ organization_id: ORGANIZATION_ID });
    Object.entries(filters).forEach(([key, value]) => {
      if (value.trim()) params.set(key, value.trim());
    });
    return params.toString();
  }, [filters]);

  async function loadData() {
    try {
      setLoading(true);
      setError(null);
      const [optionsData, listData, summaryData] = await Promise.all([
        apiGet<ExpenseOptions>(`/expenses/options?organization_id=${ORGANIZATION_ID}`),
        apiGet<ExpenseListResponse>(`/expenses?${queryString}`),
        apiGet<ExpenseSummary>(`/expenses/summary?organization_id=${ORGANIZATION_ID}&reference_date=${todayIso()}`),
      ]);
      setOptions(optionsData);
      setData(listData);
      setSummary(summaryData);
    } catch (err) {
      setError(friendlyErrorMessage(err, "No se pudieron cargar los gastos."));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, [queryString]);

  async function cancelExpense(expense: ExpenseRead) {
    const reason = window.prompt("Motivo de anulacion del gasto");
    if (!reason?.trim()) return;
    try {
      setError(null);
      setNotice(null);
      await apiPost<ExpenseRead>(`/expenses/${expense.id}/cancel`, {
        organization_id: ORGANIZATION_ID,
        reason,
      });
      setNotice("Gasto anulado. No se elimino: queda guardado para trazabilidad.");
      await loadData();
    } catch (err) {
      setError(friendlyErrorMessage(err, "No se pudo anular el gasto."));
    }
  }

  return (
    <AppShell>
      <section className="page-title">
        <div>
          <h1>Gastos</h1>
          <p>Salidas economicas que no ingresan stock al inventario.</p>
        </div>
        <div className="row-actions">
          <Link className="button secondary-button" href="/gastos/rapido">
            <Zap size={18} /> Carga rapida
          </Link>
          <Link className="button" href="/gastos/nuevo">
            <Plus size={18} /> Nuevo gasto
          </Link>
        </div>
      </section>

      <div className="stack">
        {error ? <div className="notice notice-error">{error}</div> : null}
        {notice ? <div className="notice notice-ok">{notice}</div> : null}

        <section className="dashboard-compact-grid">
          <article className="panel compact-dashboard-card">
            <h3>Total filtrado</h3>
            <div className="compact-metric">{formatMoney(data?.total ?? 0)}</div>
            <p className="muted">{data?.count ?? 0} gastos en el listado actual.</p>
          </article>
          <article className="panel compact-dashboard-card">
            <h3>Gastos del mes</h3>
            <div className="compact-metric">{formatMoney(summary?.month_total ?? 0)}</div>
            <p className="muted">ERP e historicos importados.</p>
          </article>
          <article className="panel compact-dashboard-card">
            <h3>Gastos del año</h3>
            <div className="compact-metric">{formatMoney(summary?.year_total ?? 0)}</div>
            <p className="muted">{summary?.count ?? 0} gastos confirmados.</p>
          </article>
          <article className="panel compact-dashboard-card">
            <h3>Mayor categoria</h3>
            <div className="compact-metric">{summary?.top_category_name ?? "-"}</div>
            <p className="muted">{formatMoney(summary?.top_category_total ?? 0)}</p>
          </article>
        </section>

        <section className="panel">
          <div className="section-heading expense-filter-heading">
            <h2>
              <Filter size={18} /> Filtros
            </h2>
            <button
              className="button secondary-button"
              type="button"
              onClick={() =>
                setFilters({
                  date_from: "",
                  date_to: "",
                  category_id: "",
                  payment_method_id: "",
                  supplier: "",
                  status: "",
                  origin: "",
                  q: "",
                })
              }
            >
              Limpiar
            </button>
          </div>
          <div className="filters-grid">
            <label className="field">
              <span>Desde</span>
              <input
                type="date"
                value={filters.date_from}
                onChange={(event) => setFilters((current) => ({ ...current, date_from: event.target.value }))}
              />
            </label>
            <label className="field">
              <span>Hasta</span>
              <input
                type="date"
                value={filters.date_to}
                onChange={(event) => setFilters((current) => ({ ...current, date_to: event.target.value }))}
              />
            </label>
            <label className="field">
              <span>Categoria</span>
              <select
                value={filters.category_id}
                onChange={(event) => setFilters((current) => ({ ...current, category_id: event.target.value }))}
              >
                <option value="">Todas</option>
                {options?.categories.map((category) => (
                  <option key={category.id} value={category.id}>
                    {category.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              <span>Medio de pago</span>
              <select
                value={filters.payment_method_id}
                onChange={(event) => setFilters((current) => ({ ...current, payment_method_id: event.target.value }))}
              >
                <option value="">Todos</option>
                {options?.payment_methods.map((method) => (
                  <option key={method.id} value={method.id}>
                    {method.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              <span>Proveedor o destinatario</span>
              <input
                value={filters.supplier}
                placeholder="Ej: Niter, feria, imprenta"
                onChange={(event) => setFilters((current) => ({ ...current, supplier: event.target.value }))}
              />
            </label>
            <label className="field">
              <span>Estado</span>
              <select
                value={filters.status}
                onChange={(event) => setFilters((current) => ({ ...current, status: event.target.value }))}
              >
                <option value="">Todos</option>
                <option value="confirmed">Confirmados</option>
                <option value="cancelled">Anulados</option>
              </select>
            </label>
            <label className="field">
              <span>Origen</span>
              <select
                value={filters.origin}
                onChange={(event) => setFilters((current) => ({ ...current, origin: event.target.value }))}
              >
                <option value="">Todos</option>
                <option value="system">ERP</option>
                <option value="imported">Importado</option>
              </select>
            </label>
            <label className="field expense-search-field">
              <span>Buscar</span>
              <input
                value={filters.q}
                placeholder="Descripcion, notas o proveedor"
                onChange={(event) => setFilters((current) => ({ ...current, q: event.target.value }))}
              />
            </label>
          </div>
        </section>

        <section className="panel">
          <h2>Gastos registrados</h2>
          {loading ? <div className="empty-state">Cargando gastos...</div> : null}
          {!loading && data?.items.length === 0 ? (
            <div className="empty-state">No hay gastos para los filtros seleccionados.</div>
          ) : null}
          {!loading && data && data.items.length > 0 ? (
            <div className="table-scroll">
              <table className="table">
                <thead>
                  <tr>
                    <th>Fecha</th>
                    <th>Categoria</th>
                    <th>Descripcion</th>
                    <th>Proveedor</th>
                    <th>Medio</th>
                    <th>Importe</th>
                    <th>Estado</th>
                    <th>Origen</th>
                    <th>Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((expense) => (
                    <tr key={`${expense.origin}-${expense.id}`}>
                      <td>{formatDate(expense.expense_date)}</td>
                      <td>{expense.category_name}</td>
                      <td>{expense.description}</td>
                      <td>{expense.supplier_name ?? "-"}</td>
                      <td>{expense.payment_method_name ?? "-"}</td>
                      <td>{formatMoney(expense.amount)}</td>
                      <td>
                        <span className={`status-dot ${expense.status === "cancelled" ? "status-inactive" : "status-active"}`}>
                          {statusLabel(expense.status)}
                        </span>
                      </td>
                      <td>{originLabel(expense.origin)}</td>
                      <td>
                        <div className="row-actions">
                          <Link
                            className="button secondary-button icon-button"
                            href={`/gastos/${expense.id}${expense.origin === "imported" ? "?origin=imported" : ""}`}
                            title="Ver detalle"
                          >
                            <Eye size={16} />
                          </Link>
                          {expense.editable ? (
                            <Link
                              className="button secondary-button icon-button"
                              href={`/gastos/${expense.id}/editar`}
                              title="Editar datos administrativos"
                            >
                              <Pencil size={16} />
                            </Link>
                          ) : null}
                          {expense.cancellable ? (
                            <button
                              className="button secondary-button icon-button"
                              type="button"
                              onClick={() => cancelExpense(expense)}
                              title="Anular gasto"
                            >
                              <Ban size={16} />
                            </button>
                          ) : null}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </section>
      </div>
    </AppShell>
  );
}
