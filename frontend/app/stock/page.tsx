"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, PackagePlus } from "lucide-react";

import { AppShell } from "@/components/AppShell";
import { apiGet, ORGANIZATION_ID, Resource, ResourceStock } from "@/lib/api";
import { friendlyErrorMessage } from "@/lib/messages";

type StockFilter = "all" | "raw_material" | "packaging" | "product" | "low" | "empty";

const TYPE_LABELS: Record<string, string> = {
  raw_material: "Materia prima",
  packaging: "Packaging",
  product: "Producto terminado",
  mix: "Mezcla",
};

function formatQuantity(value: string | number) {
  return Number(value || 0).toLocaleString("es-UY", { maximumFractionDigits: 3 });
}

export default function StockPage() {
  const [resources, setResources] = useState<Resource[]>([]);
  const [stock, setStock] = useState<ResourceStock[]>([]);
  const [filter, setFilter] = useState<StockFilter>("all");
  const [error, setError] = useState<string | null>(null);

  async function loadData() {
    try {
      setError(null);
      const [resourceData, stockData] = await Promise.all([
        apiGet<Resource[]>(`/resources?organization_id=${ORGANIZATION_ID}`),
        apiGet<ResourceStock[]>(`/resources/stock?organization_id=${ORGANIZATION_ID}`),
      ]);
      setResources(resourceData.filter((resource) => resource.active));
      setStock(stockData);
    } catch (err) {
      setError(friendlyErrorMessage(err, "No se pudo cargar el stock."));
    }
  }

  useEffect(() => {
    if (window.location.search.includes("filter=low")) {
      setFilter("low");
    }
    loadData();
  }, []);

  const items = useMemo(() => {
    return resources
      .map((resource) => {
        const stockRow = stock.find((item) => item.resource_id === resource.id);
        const quantity = Number(stockRow?.quantity ?? 0);
        const minimum = Number(resource.minimum_stock ?? 0);
        const low = minimum > 0 && quantity <= minimum;
        return { resource, quantity, minimum, low, empty: quantity <= 0 };
      })
      .filter((item) => {
        if (filter === "all") return true;
        if (filter === "low") return item.low;
        if (filter === "empty") return item.empty;
        return item.resource.type === filter;
      })
      .sort((a, b) => Number(b.low) - Number(a.low) || a.resource.name.localeCompare(b.resource.name));
  }, [resources, stock, filter]);

  return (
    <AppShell>
      <section className="page-title">
        <div>
          <h1>Stock</h1>
          <p>Consulta rapida de existencias y alertas.</p>
        </div>
        <Link className="button" href="/compras/rapida">
          <PackagePlus size={18} /> Registrar compra
        </Link>
      </section>

      <div className="stack">
        {error ? <div className="notice notice-error">{error}</div> : null}
        <section className="panel">
          <div className="mobile-filter-pills">
            {[
              ["all", "Todos"],
              ["raw_material", "Materias primas"],
              ["packaging", "Packaging"],
              ["product", "Productos"],
              ["low", "Stock bajo"],
              ["empty", "Sin stock"],
            ].map(([value, label]) => (
              <button
                className={`filter-pill ${filter === value ? "filter-pill-active" : ""}`}
                key={value}
                type="button"
                onClick={() => setFilter(value as StockFilter)}
              >
                {label}
              </button>
            ))}
          </div>
        </section>

        <section className="mobile-card-list">
          {items.map(({ resource, quantity, minimum, low, empty }) => (
            <article className={`mobile-record-card stock-card ${low || empty ? "mobile-alert-card" : ""}`} key={resource.id}>
              <div>
                <strong>{resource.name}</strong>
                <span>{resource.code} - {TYPE_LABELS[resource.type] ?? resource.type}</span>
                <span>Minimo: {formatQuantity(minimum)} {resource.unit}</span>
              </div>
              <div>
                <strong>{formatQuantity(quantity)} {resource.unit}</strong>
                <span>{empty ? "Sin stock" : low ? "Stock bajo" : "Normal"}</span>
                {low || empty ? (
                  <Link className="button secondary-button" href="/compras/rapida">
                    <AlertTriangle size={16} /> Comprar
                  </Link>
                ) : null}
              </div>
            </article>
          ))}
          {items.length === 0 ? <div className="panel empty-state">No hay recursos para este filtro.</div> : null}
        </section>
      </div>
    </AppShell>
  );
}
