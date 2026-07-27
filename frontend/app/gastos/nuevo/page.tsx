"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Save } from "lucide-react";

import { AppShell } from "@/components/AppShell";
import { apiGet, apiPost, ExpenseOptions, ExpenseRead, ORGANIZATION_ID } from "@/lib/api";
import { friendlyErrorMessage } from "@/lib/messages";

function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

export default function NewExpensePage() {
  const router = useRouter();
  const [options, setOptions] = useState<ExpenseOptions | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    expense_date: todayIso(),
    category_id: "",
    description: "",
    amount: "",
    payment_method_id: "",
    supplier_name: "",
    receipt_number: "",
    notes: "",
  });

  useEffect(() => {
    apiGet<ExpenseOptions>(`/expenses/options?organization_id=${ORGANIZATION_ID}`)
      .then((data) => {
        setOptions(data);
        setForm((current) => ({
          ...current,
          category_id: current.category_id || data.categories[0]?.id || "",
          payment_method_id: current.payment_method_id || data.payment_methods[0]?.id || "",
        }));
      })
      .catch((err) => setError(friendlyErrorMessage(err, "No se pudieron cargar las opciones del gasto.")));
  }, []);

  function validate() {
    if (!form.expense_date) return "Selecciona la fecha del gasto.";
    if (!form.category_id) return "Selecciona una categoria.";
    if (!form.description.trim()) return "Escribe una descripcion clara del gasto.";
    const amount = Number(form.amount);
    if (!Number.isFinite(amount) || amount <= 0) return "El importe debe ser mayor a cero.";
    if (!form.payment_method_id) return "Selecciona un medio de pago.";
    return null;
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    const validation = validate();
    if (validation) {
      setError(validation);
      return;
    }
    try {
      setSaving(true);
      setError(null);
      const expense = await apiPost<ExpenseRead>("/expenses", {
        organization_id: ORGANIZATION_ID,
        ...form,
        amount: Number(form.amount),
      });
      router.push(`/gastos/${expense.id}`);
    } catch (err) {
      setError(friendlyErrorMessage(err, "No se pudo guardar el gasto."));
    } finally {
      setSaving(false);
    }
  }

  return (
    <AppShell>
      <section className="page-title">
        <div>
          <h1>Nuevo gasto</h1>
          <p>Registra una salida economica que no modifica stock.</p>
        </div>
        <Link className="button secondary-button" href="/gastos">
          Volver
        </Link>
      </section>

      <form className="panel form wide-form" onSubmit={submit}>
        {error ? <div className="notice notice-error">{error}</div> : null}
        <div className="form-grid">
          <label className="field">
            <span>Fecha</span>
            <input
              required
              type="date"
              value={form.expense_date}
              onChange={(event) => setForm((current) => ({ ...current, expense_date: event.target.value }))}
            />
          </label>
          <label className="field">
            <span>Categoria</span>
            <select
              required
              value={form.category_id}
              onChange={(event) => setForm((current) => ({ ...current, category_id: event.target.value }))}
            >
              <option value="">Seleccionar categoria</option>
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
              required
              value={form.payment_method_id}
              onChange={(event) => setForm((current) => ({ ...current, payment_method_id: event.target.value }))}
            >
              <option value="">Seleccionar medio</option>
              {options?.payment_methods.map((method) => (
                <option key={method.id} value={method.id}>
                  {method.name}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Descripcion</span>
            <input
              required
              value={form.description}
              placeholder="Ej: impresiones para feria"
              onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))}
            />
          </label>
          <label className="field">
            <span>Importe</span>
            <input
              required
              min="0.01"
              step="0.01"
              type="number"
              value={form.amount}
              onChange={(event) => setForm((current) => ({ ...current, amount: event.target.value }))}
            />
          </label>
          <label className="field">
            <span>Proveedor o destinatario</span>
            <input
              list="expense-suppliers"
              value={form.supplier_name}
              placeholder="Opcional"
              onChange={(event) => setForm((current) => ({ ...current, supplier_name: event.target.value }))}
            />
            <datalist id="expense-suppliers">
              {options?.suppliers.map((supplier) => <option key={supplier} value={supplier} />)}
            </datalist>
          </label>
          <label className="field">
            <span>Comprobante</span>
            <input
              value={form.receipt_number}
              placeholder="Opcional"
              onChange={(event) => setForm((current) => ({ ...current, receipt_number: event.target.value }))}
            />
          </label>
        </div>
        <label className="field">
          <span>Observaciones</span>
          <textarea
            rows={4}
            value={form.notes}
            placeholder="Opcional"
            onChange={(event) => setForm((current) => ({ ...current, notes: event.target.value }))}
          />
        </label>
        <button className="button" type="submit" disabled={saving}>
          <Save size={18} /> {saving ? "Guardando..." : "Guardar gasto"}
        </button>
      </form>
    </AppShell>
  );
}
