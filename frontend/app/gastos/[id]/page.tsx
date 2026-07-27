"use client";

import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { Ban, Pencil } from "lucide-react";

import { AppShell } from "@/components/AppShell";
import { apiGet, apiPost, ExpenseRead, ORGANIZATION_ID } from "@/lib/api";
import { friendlyErrorMessage } from "@/lib/messages";

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

export default function ExpenseDetailPage() {
  const params = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const [expense, setExpense] = useState<ExpenseRead | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const origin = searchParams.get("origin");

  async function loadExpense() {
    try {
      setError(null);
      const originQuery = origin ? `&origin=${origin}` : "";
      const data = await apiGet<ExpenseRead>(`/expenses/${params.id}?organization_id=${ORGANIZATION_ID}${originQuery}`);
      setExpense(data);
    } catch (err) {
      setError(friendlyErrorMessage(err, "No se pudo cargar el gasto."));
    }
  }

  useEffect(() => {
    loadExpense();
  }, [params.id, origin]);

  async function cancelExpense() {
    if (!expense) return;
    const reason = window.prompt("Motivo de anulacion del gasto");
    if (!reason?.trim()) return;
    try {
      setError(null);
      await apiPost<ExpenseRead>(`/expenses/${expense.id}/cancel`, {
        organization_id: ORGANIZATION_ID,
        reason,
      });
      setNotice("Gasto anulado. Queda conservado para trazabilidad.");
      await loadExpense();
    } catch (err) {
      setError(friendlyErrorMessage(err, "No se pudo anular el gasto."));
    }
  }

  return (
    <AppShell>
      <section className="page-title">
        <div>
          <h1>Detalle del gasto</h1>
          <p>Consulta de un gasto sin afectar el inventario.</p>
        </div>
        <Link className="button secondary-button" href="/gastos">
          Volver
        </Link>
      </section>

      <div className="stack">
        {error ? <div className="notice notice-error">{error}</div> : null}
        {notice ? <div className="notice notice-ok">{notice}</div> : null}
        {!expense && !error ? <div className="panel empty-state">Cargando gasto...</div> : null}
        {expense ? (
          <section className="panel expense-detail">
            <div className="expense-detail-header">
              <div>
                <span className={`status-dot ${expense.status === "cancelled" ? "status-inactive" : "status-active"}`}>
                  {expense.status === "cancelled" ? "Anulado" : "Confirmado"}
                </span>
                <span className="status-dot status-neutral">{expense.origin === "imported" ? "Importado" : "ERP"}</span>
              </div>
              <div className="row-actions">
                {expense.editable ? (
                  <Link className="button secondary-button" href={`/gastos/${expense.id}/editar`}>
                    <Pencil size={16} /> Editar datos
                  </Link>
                ) : null}
                {expense.cancellable ? (
                  <button className="button secondary-button" type="button" onClick={cancelExpense}>
                    <Ban size={16} /> Anular
                  </button>
                ) : null}
              </div>
            </div>

            <div className="expense-detail-main">
              <div>
                <h2>{expense.description}</h2>
                <p className="muted">{expense.category_name}</p>
              </div>
              <strong>{formatMoney(expense.amount)}</strong>
            </div>

            <div className="resource-card-grid">
              <div className="compact-field">
                <span>Fecha</span>
                <strong>{formatDate(expense.expense_date)}</strong>
              </div>
              <div className="compact-field">
                <span>Medio de pago</span>
                <strong>{expense.payment_method_name ?? "-"}</strong>
              </div>
              <div className="compact-field">
                <span>Proveedor o destinatario</span>
                <strong>{expense.supplier_name ?? "-"}</strong>
              </div>
              <div className="compact-field">
                <span>Comprobante</span>
                <strong>{expense.receipt_number ?? "-"}</strong>
              </div>
              <div className="compact-field">
                <span>Origen</span>
                <strong>{expense.source_label ?? (expense.origin === "imported" ? "Importado" : "ERP")}</strong>
              </div>
            </div>

            {expense.notes ? (
              <div>
                <h3>Observaciones</h3>
                <p>{expense.notes}</p>
              </div>
            ) : null}

            {expense.cancellation_reason ? (
              <div className="notice notice-error">
                Motivo de anulacion: {expense.cancellation_reason}
              </div>
            ) : null}
          </section>
        ) : null}
      </div>
    </AppShell>
  );
}
