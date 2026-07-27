"use client";

import { useEffect, useState } from "react";

import { AppShell } from "@/components/AppShell";
import { apiGet, InventoryMovementRead, ORGANIZATION_ID } from "@/lib/api";
import { friendlyErrorMessage } from "@/lib/messages";

const FILTERS = [
  ["", "Todos"],
  ["compras", "Compras"],
  ["ventas", "Ventas"],
  ["produccion", "Produccion"],
  ["ajustes", "Ajustes"],
  ["anulaciones", "Anulaciones"],
];

function formatDate(value: string) {
  return new Date(value).toLocaleString("es-UY", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatQuantity(value: string | number) {
  return Number(value || 0).toLocaleString("es-UY", { maximumFractionDigits: 3 });
}

export default function MovementsPage() {
  const [filter, setFilter] = useState("");
  const [items, setItems] = useState<InventoryMovementRead[]>([]);
  const [error, setError] = useState<string | null>(null);

  async function loadData(nextFilter = filter) {
    try {
      setError(null);
      const params = new URLSearchParams({ organization_id: ORGANIZATION_ID });
      if (nextFilter) params.set("type_group", nextFilter);
      const data = await apiGet<InventoryMovementRead[]>(`/movements?${params.toString()}`);
      setItems(data);
    } catch (err) {
      setError(friendlyErrorMessage(err, "No se pudieron cargar los movimientos."));
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  return (
    <AppShell>
      <section className="page-title">
        <div>
          <h1>Movimientos</h1>
          <p>Actividad reciente del inventario. Solo consulta.</p>
        </div>
      </section>

      <div className="stack">
        {error ? <div className="notice notice-error">{error}</div> : null}
        <section className="panel">
          <div className="mobile-filter-pills">
            {FILTERS.map(([value, label]) => (
              <button
                className={`filter-pill ${filter === value ? "filter-pill-active" : ""}`}
                key={value}
                type="button"
                onClick={() => {
                  setFilter(value);
                  loadData(value);
                }}
              >
                {label}
              </button>
            ))}
          </div>
        </section>

        <section className="mobile-card-list">
          {items.map((item) => (
            <article className="mobile-record-card movement-card" key={item.id}>
              <div>
                <strong>{item.resource_name}</strong>
                <span>{item.resource_code} - {item.type}</span>
                <span>{formatDate(item.occurred_at)}</span>
                <span>{item.document_label ?? item.origin}</span>
              </div>
              <div>
                <strong>{formatQuantity(item.quantity)} {item.unit}</strong>
                <span>{item.origin}</span>
              </div>
            </article>
          ))}
          {items.length === 0 ? <div className="panel empty-state">No hay movimientos para este filtro.</div> : null}
        </section>
      </div>
    </AppShell>
  );
}
