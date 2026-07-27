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

export default function QuickExpensePage() {
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
      .catch((err) => setError(friendlyErrorMessage(err, "No se pudieron cargar las opciones.")));
  }, []);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    const amount = Number(form.amount);
    if (!form.expense_date) return setError("Selecciona la fecha del gasto.");
    if (!form.category_id) return setError("Selecciona una categoria.");
    if (!form.description.trim()) return setError("Escribe una descripcion corta.");
    if (!Number.isFinite(amount) || amount <= 0) return setError("El importe debe ser mayor a cero.");
    if (!form.payment_method_id) return setError("Selecciona un medio de pago.");

    try {
      setSaving(true);
      setError(null);
      await apiPost<ExpenseRead>("/expenses", {
        organization_id: ORGANIZATION_ID,
        ...form,
        amount,
      });
      router.push("/gastos");
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
          <h1>Carga rapida</h1>
          <p>Para registrar un gasto pequeño desde el telefono en menos de un minuto.</p>
        </div>
        <Link className="button secondary-button" href="/gastos">
          Volver
        </Link>
      </section>

      <form className="panel form quick-expense-form" noValidate onSubmit={submit}>
        {error ? <div className="notice notice-error">{error}</div> : null}
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
            <option value="">Seleccionar</option>
            {options?.categories.map((category) => (
              <option key={category.id} value={category.id}>
                {category.name}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>Descripcion corta</span>
          <input
            required
            value={form.description}
            placeholder="Ej: taxi feria"
            onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))}
          />
        </label>
        <label className="field">
          <span>Importe</span>
          <input
            required
            inputMode="decimal"
            min="0.01"
            step="0.01"
            type="number"
            value={form.amount}
            onChange={(event) => setForm((current) => ({ ...current, amount: event.target.value }))}
          />
        </label>
        <label className="field">
          <span>Medio de pago</span>
          <select
            required
            value={form.payment_method_id}
            onChange={(event) => setForm((current) => ({ ...current, payment_method_id: event.target.value }))}
          >
            <option value="">Seleccionar</option>
            {options?.payment_methods.map((method) => (
              <option key={method.id} value={method.id}>
                {method.name}
              </option>
            ))}
          </select>
        </label>
        <button className="button quick-save-button" type="submit" disabled={saving}>
          <Save size={18} /> {saving ? "Guardando..." : "Guardar"}
        </button>
      </form>
    </AppShell>
  );
}
