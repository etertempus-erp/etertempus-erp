"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { ClipboardCheck } from "lucide-react";

import { AppShell } from "@/components/AppShell";
import { apiGet, apiPost, FormulaDetail, FormulaSummary, ORGANIZATION_ID, Resource, ResourceStock } from "@/lib/api";
import { friendlyErrorMessage } from "@/lib/messages";
import { useUnsavedChangesWarning } from "@/lib/useUnsavedChangesWarning";

type PreviewLine = {
  resource_id: string;
  name: string;
  required: number;
  available: number;
  unit: string;
};

function formatNumber(value: number | string) {
  return Number(value || 0).toLocaleString("es-UY", { maximumFractionDigits: 4 });
}

export default function QuickProductionPage() {
  const [resources, setResources] = useState<Resource[]>([]);
  const [stock, setStock] = useState<ResourceStock[]>([]);
  const [formulas, setFormulas] = useState<FormulaSummary[]>([]);
  const [formulaDetail, setFormulaDetail] = useState<FormulaDetail | null>(null);
  const [productId, setProductId] = useState("");
  const [formulaId, setFormulaId] = useState("");
  const [elaborationDate, setElaborationDate] = useState(new Date().toISOString().slice(0, 10));
  const [targetWeight, setTargetWeight] = useState("400");
  const [notes, setNotes] = useState("");
  const [preview, setPreview] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const products = resources.filter((resource) => resource.type === "product" && resource.active);
  const formulasForSelectedProduct = formulas.filter((formula) => formula.product_resource_id === productId);

  const previewLines = useMemo<PreviewLine[]>(() => {
    return Object.entries(preview).map(([resourceId, grams]) => {
      const resource = resources.find((item) => item.id === resourceId);
      const stockRow = stock.find((item) => item.resource_id === resourceId);
      return {
        resource_id: resourceId,
        name: resource?.name ?? resourceId,
        required: Number(grams || 0),
        available: Number(stockRow?.quantity ?? 0),
        unit: resource?.unit ?? "g",
      };
    });
  }, [preview, resources, stock]);

  const hasInsufficientStock = previewLines.some((line) => line.available < line.required);
  const hasUnsavedChanges =
    Boolean(productId) ||
    Boolean(formulaId) ||
    targetWeight !== "400" ||
    Boolean(notes.trim()) ||
    previewLines.length > 0;

  useUnsavedChangesWarning(hasUnsavedChanges && !saving);

  async function loadData() {
    try {
      setError(null);
      const [resourceData, formulaData, stockData] = await Promise.all([
        apiGet<Resource[]>(`/resources?organization_id=${ORGANIZATION_ID}`),
        apiGet<FormulaSummary[]>(`/formulas?organization_id=${ORGANIZATION_ID}`),
        apiGet<ResourceStock[]>(`/resources/stock?organization_id=${ORGANIZATION_ID}`),
      ]);
      setResources(resourceData);
      setFormulas(formulaData);
      setStock(stockData);
    } catch (err) {
      setError(friendlyErrorMessage(err, "No se pudieron cargar los datos de produccion."));
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  async function loadFormula(nextFormulaId: string, nextWeight = targetWeight) {
    setFormulaId(nextFormulaId);
    setPreview({});
    setFormulaDetail(null);
    if (!nextFormulaId) return;
    if (Number(nextWeight) <= 0) return setError("El peso a producir debe ser mayor a cero.");
    try {
      setError(null);
      const [detail, scaled] = await Promise.all([
        apiGet<FormulaDetail>(`/formulas/${nextFormulaId}`),
        apiPost<{ ingredient_grams: Record<string, string> }>(`/formulas/${nextFormulaId}/scale`, {
          target_weight: Number(nextWeight),
        }),
      ]);
      setFormulaDetail(detail);
      setPreview(scaled.ingredient_grams);
    } catch (err) {
      setError(friendlyErrorMessage(err, "No se pudo calcular la formula."));
    }
  }

  async function recalculate(nextWeight: string) {
    setTargetWeight(nextWeight);
    if (formulaId) await loadFormula(formulaId, nextWeight);
  }

  async function createBatch() {
    if (saving) return;
    setSaving(true);
    setError(null);
    setMessage(null);
    if (!productId) {
      setSaving(false);
      return setError("Selecciona el producto.");
    }
    if (!formulaId) {
      setSaving(false);
      return setError("Selecciona la formula.");
    }
    if (!targetWeight || Number(targetWeight) <= 0) {
      setSaving(false);
      return setError("El peso a producir debe ser mayor a cero.");
    }
    if (hasInsufficientStock) {
      setSaving(false);
      return setError("Hay ingredientes con stock insuficiente. El lote no se registro.");
    }

    try {
      await apiPost("/production/batches", {
        organization_id: ORGANIZATION_ID,
        product_resource_id: productId,
        formula_id: formulaId,
        elaboration_date: elaborationDate,
        target_weight: Number(targetWeight),
        notes: notes.trim() || null,
      });
      setMessage("Lote creado. Las materias primas fueron consumidas.");
      setPreview({});
      setFormulaDetail(null);
      const stockData = await apiGet<ResourceStock[]>(`/resources/stock?organization_id=${ORGANIZATION_ID}`);
      setStock(stockData);
    } catch (err) {
      setError(friendlyErrorMessage(err, "No se pudo crear el lote."));
    } finally {
      setSaving(false);
    }
  }

  return (
    <AppShell>
      <section className="page-title">
        <div>
          <h1>Produccion rapida</h1>
          <p>Crea un lote desde el celular revisando stock antes de confirmar.</p>
        </div>
        <Link className="button secondary-button" href="/produccion">
          Ver produccion
        </Link>
      </section>

      <div className="stack mobile-operation">
        {message ? <div className="notice notice-ok">{message}</div> : null}
        {error ? <div className="notice notice-error">{error}</div> : null}

        <section className="panel form">
          <label className="field">
            <span>Producto</span>
            <select
              value={productId}
              onChange={(event) => {
                setProductId(event.target.value);
                setFormulaId("");
                setFormulaDetail(null);
                setPreview({});
              }}
            >
              <option value="">Seleccionar producto</option>
              {products.map((product) => (
                <option key={product.id} value={product.id}>{product.name}</option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Formula</span>
            <select value={formulaId} onChange={(event) => loadFormula(event.target.value)}>
              <option value="">{productId ? "Seleccionar version" : "Primero selecciona producto"}</option>
              {formulasForSelectedProduct.map((formula) => (
                <option key={formula.id} value={formula.id}>
                  {formula.name} v{formula.version}{formula.active_version ? " - activa" : ""}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Fecha de elaboracion</span>
            <input type="date" value={elaborationDate} onChange={(event) => setElaborationDate(event.target.value)} />
          </label>
          <label className="field">
            <span>Peso a producir</span>
            <input inputMode="decimal" type="number" min="0.001" step="0.001" value={targetWeight} onChange={(event) => recalculate(event.target.value)} />
          </label>
          <label className="field">
            <span>Observacion opcional</span>
            <input value={notes} onChange={(event) => setNotes(event.target.value)} />
          </label>
        </section>

        <section className="panel">
          <h2>Ingredientes requeridos</h2>
          {formulaDetail ? <p className="muted">{formulaDetail.name} v{formulaDetail.version}</p> : null}
          <div className="mobile-card-list">
            {previewLines.map((line) => {
              const low = line.available < line.required;
              return (
                <article className={`mobile-record-card ${low ? "mobile-alert-card" : ""}`} key={line.resource_id}>
                  <div>
                    <strong>{line.name}</strong>
                    <span>Necesario: {formatNumber(line.required)} {line.unit}</span>
                  </div>
                  <div>
                    <strong>{formatNumber(line.available)} {line.unit}</strong>
                    <span>{low ? "Stock insuficiente" : "Stock disponible"}</span>
                  </div>
                </article>
              );
            })}
            {previewLines.length === 0 ? <div className="empty-state">Selecciona una formula para ver ingredientes.</div> : null}
          </div>
          {hasInsufficientStock ? (
            <div className="notice notice-error">Hay ingredientes insuficientes. Registra una compra antes de producir.</div>
          ) : null}
          <button className="button touch-button" type="button" onClick={createBatch} disabled={saving || !productId || !formulaId}>
            <ClipboardCheck size={18} /> {saving ? "Creando..." : "Confirmar lote"}
          </button>
        </section>
      </div>
    </AppShell>
  );
}
