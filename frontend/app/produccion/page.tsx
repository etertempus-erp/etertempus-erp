"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ClipboardCheck, Zap } from "lucide-react";

import { AppShell } from "@/components/AppShell";
import { apiGet, apiPost, FormulaSummary, ORGANIZATION_ID, Resource } from "@/lib/api";
import { friendlyErrorMessage } from "@/lib/messages";

export default function ProductionPage() {
  const [resources, setResources] = useState<Resource[]>([]);
  const [formulas, setFormulas] = useState<FormulaSummary[]>([]);
  const [productId, setProductId] = useState("");
  const [formulaId, setFormulaId] = useState("");
  const [elaborationDate, setElaborationDate] = useState(new Date().toISOString().slice(0, 10));
  const [targetWeight, setTargetWeight] = useState("400");
  const [preview, setPreview] = useState<Record<string, string>>({});
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const products = resources.filter((resource) => resource.type === "product" && resource.active);
  const formulasForSelectedProduct = formulas.filter((formula) => formula.product_resource_id === productId);

  async function loadData() {
    try {
      setError(null);
      const [resourceData, formulaData] = await Promise.all([
        apiGet<Resource[]>(`/resources?organization_id=${ORGANIZATION_ID}`),
        apiGet<FormulaSummary[]>(`/formulas?organization_id=${ORGANIZATION_ID}`),
      ]);
      setResources(resourceData);
      setFormulas(formulaData);
    } catch (err) {
      setError(friendlyErrorMessage(err, "No se pudieron cargar los datos."));
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  async function scaleFormula(nextFormulaId = formulaId, nextTargetWeight = targetWeight) {
    if (!nextFormulaId || !nextTargetWeight) {
      setPreview({});
      return;
    }
    if (Number(nextTargetWeight) <= 0) {
      setPreview({});
      setError("El peso a elaborar debe ser mayor a cero. No se permiten numeros negativos.");
      return;
    }

    try {
      setError(null);
      const data = await apiPost<{ ingredient_grams: Record<string, string> }>(
        `/formulas/${nextFormulaId}/scale`,
        { target_weight: Number(nextTargetWeight) },
      );
      setPreview(data.ingredient_grams);
    } catch (err) {
      setPreview({});
      setError(friendlyErrorMessage(err, "No se pudo calcular la formula."));
    }
  }

  async function createBatch() {
    setLoading(true);
    setMessage(null);
    setError(null);

    const product = products.find((item) => item.id === productId);
    const formula = formulasForSelectedProduct.find((item) => item.id === formulaId);

    if (!product) {
      setError("Selecciona un producto activo antes de crear el lote.");
      setLoading(false);
      return;
    }

    if (!formula) {
      setError("Selecciona una version de formula asociada a este producto.");
      setLoading(false);
      return;
    }

    if (!targetWeight || Number(targetWeight) <= 0) {
      setError("Indica un peso a elaborar mayor a cero.");
      setLoading(false);
      return;
    }

    try {
      await apiPost("/production/batches", {
        organization_id: ORGANIZATION_ID,
        product_resource_id: productId,
        formula_id: formulaId,
        elaboration_date: elaborationDate,
        target_weight: Number(targetWeight),
      });
      setMessage("Lote creado.");
      setPreview({});
    } catch (err) {
      setError(friendlyErrorMessage(err, "No se pudo crear el lote."));
    } finally {
      setLoading(false);
    }
  }

  function ingredientName(id: string) {
    return resources.find((resource) => resource.id === id)?.name ?? id;
  }

  return (
    <AppShell>
      <section className="page-title">
        <div>
          <h1>Nueva produccion</h1>
          <p>El lote nace cuando se elabora la mezcla.</p>
        </div>
        <Link className="button" href="/produccion/rapida">
          <Zap size={18} /> Produccion rapida
        </Link>
      </section>

      <div className="stack">
        {message ? <div className="notice notice-ok">{message}</div> : null}
        {error ? <div className="notice notice-error">{error}</div> : null}

        <section className="panel">
          <h2>Crear lote</h2>
          <form className="form" onSubmit={(event) => event.preventDefault()}>
            <div className="field">
              <label htmlFor="product">Producto</label>
              <select
                id="product"
                value={productId}
                onChange={(event) => {
                  setProductId(event.target.value);
                  setFormulaId("");
                  setPreview({});
                }}
              >
                <option value="">Seleccionar producto</option>
                {products.map((product) => (
                  <option key={product.id} value={product.id}>
                    {product.name}
                  </option>
                ))}
              </select>
              <span className="muted">Solo se muestran productos activos.</span>
            </div>
            <div className="field">
              <label htmlFor="formula">Formula</label>
              <select
                id="formula"
                value={formulaId}
                onChange={(event) => {
                  setFormulaId(event.target.value);
                  scaleFormula(event.target.value, targetWeight);
                }}
              >
                <option value="">
                  {productId ? "Seleccionar version" : "Primero selecciona un producto"}
                </option>
                {formulasForSelectedProduct.map((formula) => (
                  <option key={formula.id} value={formula.id}>
                    {formula.name} v{formula.version}
                    {formula.active_version ? " - activa" : ""}
                  </option>
                ))}
              </select>
              {productId && formulasForSelectedProduct.length === 0 ? (
                <span className="muted">Este producto todavia no tiene formulas registradas.</span>
              ) : null}
            </div>
            <div className="field">
              <label htmlFor="date">Fecha de elaboracion</label>
              <input
                id="date"
                type="date"
                value={elaborationDate}
                onChange={(event) => setElaborationDate(event.target.value)}
              />
            </div>
            <div className="field">
              <label htmlFor="weight">Peso a elaborar</label>
              <input
                id="weight"
                type="number"
                min="1"
                value={targetWeight}
                onChange={(event) => {
                  setTargetWeight(event.target.value);
                  scaleFormula(formulaId, event.target.value);
                }}
              />
            </div>

            <section className="panel">
              <h2>Vista previa</h2>
              <div className="table-scroll">
              <table className="table">
                <tbody>
                  {Object.entries(preview).map(([resourceId, grams]) => (
                    <tr key={resourceId}>
                      <td>{ingredientName(resourceId)}</td>
                      <td>{grams} g</td>
                    </tr>
                  ))}
                  {Object.keys(preview).length === 0 ? (
                    <tr>
                      <td className="muted">Selecciona una formula para calcular los gramos.</td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
              </div>
            </section>

            <button
              className="button"
              type="button"
              onClick={createBatch}
              disabled={loading || !productId || !formulaId}
            >
              <ClipboardCheck size={18} /> {loading ? "Creando..." : "Confirmar lote"}
            </button>
          </form>
        </section>
      </div>
    </AppShell>
  );
}
