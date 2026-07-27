"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Save } from "lucide-react";

import { AppShell } from "@/components/AppShell";
import { apiGet, apiPut, ExpenseOptions, ExpenseRead, ORGANIZATION_ID } from "@/lib/api";
import { friendlyErrorMessage } from "@/lib/messages";

export default function EditExpensePage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [options, setOptions] = useState<ExpenseOptions | null>(null);
  const [expense, setExpense] = useState<ExpenseRead | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    supplier_name: "",
    receipt_number: "",
    notes: "",
  });

  useEffect(() => {
    Promise.all([
      apiGet<ExpenseRead>(`/expenses/${params.id}?organization_id=${ORGANIZATION_ID}`),
      apiGet<ExpenseOptions>(`/expenses/options?organization_id=${ORGANIZATION_ID}`),
    ])
      .then(([expenseData, optionsData]) => {
        setExpense(expenseData);
        setOptions(optionsData);
        setForm({
          supplier_name: expenseData.supplier_name ?? "",
          receipt_number: expenseData.receipt_number ?? "",
          notes: expenseData.notes ?? "",
        });
      })
      .catch((err) => setError(friendlyErrorMessage(err, "No se pudo cargar el gasto.")));
  }, [params.id]);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    try {
      setSaving(true);
      setError(null);
      await apiPut<ExpenseRead>(`/expenses/${params.id}`, {
        organization_id: ORGANIZATION_ID,
        ...form,
      });
      router.push(`/gastos/${params.id}`);
    } catch (err) {
      setError(friendlyErrorMessage(err, "No se pudo guardar el cambio."));
    } finally {
      setSaving(false);
    }
  }

  return (
    <AppShell>
      <section className="page-title">
        <div>
          <h1>Editar gasto</h1>
          <p>Solo se editan datos administrativos. Importe, fecha y categoria quedan protegidos.</p>
        </div>
        <Link className="button secondary-button" href={expense ? `/gastos/${expense.id}` : "/gastos"}>
          Volver
        </Link>
      </section>

      <form className="panel form" onSubmit={submit}>
        {error ? <div className="notice notice-error">{error}</div> : null}
        {expense ? (
          <div className="notice">
            {expense.description} - {expense.category_name} - ${expense.amount}
          </div>
        ) : null}
        <label className="field">
          <span>Proveedor o destinatario</span>
          <input
            list="expense-edit-suppliers"
            value={form.supplier_name}
            onChange={(event) => setForm((current) => ({ ...current, supplier_name: event.target.value }))}
          />
          <datalist id="expense-edit-suppliers">
            {options?.suppliers.map((supplier) => <option key={supplier} value={supplier} />)}
          </datalist>
        </label>
        <label className="field">
          <span>Comprobante</span>
          <input
            value={form.receipt_number}
            onChange={(event) => setForm((current) => ({ ...current, receipt_number: event.target.value }))}
          />
        </label>
        <label className="field">
          <span>Observaciones</span>
          <textarea
            rows={4}
            value={form.notes}
            onChange={(event) => setForm((current) => ({ ...current, notes: event.target.value }))}
          />
        </label>
        <button className="button" type="submit" disabled={saving || !expense?.editable}>
          <Save size={18} /> {saving ? "Guardando..." : "Guardar cambios"}
        </button>
      </form>
    </AppShell>
  );
}
