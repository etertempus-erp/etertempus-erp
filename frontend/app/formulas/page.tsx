"use client";

import { useEffect, useMemo, useState } from "react";
import { Plus, Save, Trash2 } from "lucide-react";

import { AppShell } from "@/components/AppShell";
import { apiGet, apiPost, FormulaDetail, FormulaSummary, ORGANIZATION_ID, Resource, ResourceStock } from "@/lib/api";
import { friendlyErrorMessage } from "@/lib/messages";

type FormulaItemForm = {
  ingredient_resource_id: string;
  percentage: string;
};

type FormulaForm = {
  name: string;
  version: string;
  product_resource_id: string;
  status: "draft" | "active" | "archived";
  active_version: boolean;
  items: FormulaItemForm[];
};

const initialForm: FormulaForm = {
  name: "",
  version: "1",
  product_resource_id: "",
  status: "draft",
  active_version: false,
  items: [{ ingredient_resource_id: "", percentage: "" }],
};

function removeAccents(value: string) {
  return value.normalize("NFD").replace(/[\u0300-\u036f]/g, "");
}

function formatPercent(value: number | string) {
  return Number(value).toLocaleString("es-UY", {
    maximumFractionDigits: 2,
  });
}

function hasMoreThanTwoDecimals(value: string) {
  const [, decimalPart = ""] = value.replace(",", ".").split(".");
  return decimalPart.length > 2;
}

export default function FormulasPage() {
  const [form, setForm] = useState<FormulaForm>(initialForm);
  const [resources, setResources] = useState<Resource[]>([]);
  const [stock, setStock] = useState<ResourceStock[]>([]);
  const [formulas, setFormulas] = useState<FormulaSummary[]>([]);
  const [formulaDetails, setFormulaDetails] = useState<Record<string, FormulaDetail>>({});
  const [selectedFormula, setSelectedFormula] = useState<FormulaDetail | null>(null);
  const [detailTargetWeight, setDetailTargetWeight] = useState("20");
  const [targetWeight, setTargetWeight] = useState("400");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const ingredients = resources.filter((resource) => resource.type === "raw_material");
  const products = resources.filter((resource) => resource.type === "product");

  const totalPercentage = useMemo(
    () => form.items.reduce((sum, item) => sum + Number(item.percentage || 0), 0),
    [form.items],
  );

  async function loadData() {
    try {
      setError(null);
      const [resourceData, formulaData] = await Promise.all([
        apiGet<Resource[]>(`/resources?organization_id=${ORGANIZATION_ID}`),
        apiGet<FormulaSummary[]>(`/formulas?organization_id=${ORGANIZATION_ID}`),
      ]);
      const [stockData, detailRows] = await Promise.all([
        apiGet<ResourceStock[]>(`/resources/stock?organization_id=${ORGANIZATION_ID}`),
        Promise.all(
          formulaData.map((formula) =>
            apiGet<FormulaDetail>(`/formulas/${formula.id}`).catch(() => null),
          ),
        ),
      ]);
      setResources(resourceData);
      setStock(stockData);
      setFormulas(formulaData);
      setFormulaDetails(
        Object.fromEntries(detailRows.filter(Boolean).map((detail) => [detail!.id, detail!])) as Record<string, FormulaDetail>,
      );
    } catch (err) {
      setError(friendlyErrorMessage(err, "No se pudieron cargar los datos."));
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  function updateItem(index: number, item: Partial<FormulaItemForm>) {
    setForm({
      ...form,
      items: form.items.map((current, currentIndex) =>
        currentIndex === index ? { ...current, ...item } : current,
      ),
    });
  }

  function addItem() {
    setForm({
      ...form,
      items: [...form.items, { ingredient_resource_id: "", percentage: "" }],
    });
  }

  function removeItem(index: number) {
    setForm({
      ...form,
      items: form.items.filter((_, currentIndex) => currentIndex !== index),
    });
  }

  async function saveFormula() {
    setLoading(true);
    setMessage(null);
    setError(null);

    if (!form.name.trim()) {
      setError("Ponle un nombre a la formula antes de guardarla.");
      setLoading(false);
      return;
    }

    if (form.items.some((item) => !item.ingredient_resource_id || !item.percentage)) {
      setError("Cada ingrediente necesita un recurso y un porcentaje.");
      setLoading(false);
      return;
    }

    if (Number(form.version || 0) < 1) {
      setError("La version debe ser 1 o mayor. No se permiten numeros negativos.");
      setLoading(false);
      return;
    }

    if (Number(targetWeight || 0) <= 0) {
      setError("La vista en gramos debe ser mayor a cero.");
      setLoading(false);
      return;
    }

    if (form.items.some((item) => Number(item.percentage || 0) <= 0)) {
      setError("Los porcentajes deben ser mayores a cero. No se permiten valores negativos.");
      setLoading(false);
      return;
    }

    if (form.items.some((item) => hasMoreThanTwoDecimals(item.percentage))) {
      setError("Los porcentajes pueden tener como maximo 2 decimales.");
      setLoading(false);
      return;
    }

    if (totalPercentage !== 100) {
      setError("La formula todavia no cierra: los porcentajes deben sumar exactamente 100%.");
      setLoading(false);
      return;
    }

    if (
      formulas.some(
        (formula) =>
          formula.name.toLowerCase() === form.name.trim().toLowerCase() &&
          formula.version === Number(form.version),
      )
    ) {
      setError("Ya existe una formula con ese nombre y esa version. Crea una nueva version antes de guardar.");
      setLoading(false);
      return;
    }

    try {
      await apiPost("/formulas", {
        organization_id: ORGANIZATION_ID,
        name: removeAccents(form.name.trim()),
        version: Number(form.version),
        product_resource_id: form.product_resource_id || null,
        status: form.status,
        active_version: form.active_version,
        items: form.items.map((item, index) => ({
          ingredient_resource_id: item.ingredient_resource_id,
          percentage: Number(item.percentage),
          sort_order: index + 1,
        })),
      });
      setForm(initialForm);
      setMessage("Formula guardada.");
      await loadData();
    } catch (err) {
      setError(friendlyErrorMessage(err, "No se pudo guardar la formula."));
    } finally {
      setLoading(false);
    }
  }

  async function selectFormula(formula: FormulaSummary) {
    setLoading(true);
    setMessage(null);
    setError(null);

    try {
      const detail = await apiGet<FormulaDetail>(`/formulas/${formula.id}`);
      setSelectedFormula(detail);
    } catch (err) {
      setError(friendlyErrorMessage(err, "No se pudo abrir la formula."));
    } finally {
      setLoading(false);
    }
  }

  function stockFor(resourceId: string) {
    return stock.find((item) => item.resource_id === resourceId)?.quantity ?? "0";
  }

  function detailFor(formula: FormulaSummary) {
    return formulaDetails[formula.id];
  }

  return (
    <AppShell>
      <section className="page-title">
        <div>
          <h1>Formulas</h1>
          <p>Las formulas se guardan en porcentaje y se escalan a gramos.</p>
        </div>
      </section>

      <div className="stack">
        {message ? <div className="notice notice-ok">{message}</div> : null}
        {error ? <div className="notice notice-error">{error}</div> : null}

        <section className="panel">
          <h2>Nueva formula</h2>
          <form className="form" onSubmit={(event) => event.preventDefault()}>
            <div className="field">
              <label htmlFor="name">Nombre</label>
              <input
                id="name"
                placeholder="Rosa del Alba"
                value={form.name}
                onChange={(event) => setForm({ ...form, name: event.target.value })}
              />
            </div>
            <div className="field">
              <label htmlFor="product">Producto asociado</label>
              <select
                id="product"
                value={form.product_resource_id}
                onChange={(event) => setForm({ ...form, product_resource_id: event.target.value })}
              >
                <option value="">Experimental / sin producto</option>
                {products.map((product) => (
                  <option key={product.id} value={product.id}>
                    {product.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label htmlFor="version">Version</label>
              <input
                id="version"
                type="number"
                min="1"
                value={form.version}
                onChange={(event) => setForm({ ...form, version: event.target.value })}
              />
            </div>
            <div className="field">
              <label htmlFor="status">Estado</label>
              <select
                id="status"
                value={form.status}
                onChange={(event) =>
                  setForm({ ...form, status: event.target.value as FormulaForm["status"] })
                }
              >
                <option value="draft">Borrador</option>
                <option value="active">Activa</option>
                <option value="archived">Archivada</option>
              </select>
            </div>

            <div className="field">
              <label htmlFor="targetWeight">Vista en gramos para</label>
              <input
                id="targetWeight"
                type="number"
                min="1"
                value={targetWeight}
                onChange={(event) => setTargetWeight(event.target.value)}
              />
            </div>

            <div className="table-scroll desktop-table">
            <table className="table">
              <thead>
                <tr>
                  <th>Ingrediente</th>
                  <th>%</th>
                  <th>g calculados</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {form.items.map((item, index) => (
                  <tr key={index}>
                    <td>
                      <select
                        className="inline-input"
                        value={item.ingredient_resource_id}
                        onChange={(event) =>
                          updateItem(index, { ingredient_resource_id: event.target.value })
                        }
                      >
                        <option value="">Seleccionar</option>
                        {ingredients.map((ingredient) => (
                          <option key={ingredient.id} value={ingredient.id}>
                            {ingredient.name}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td>
                      <input
                        className="inline-input"
                        type="number"
                        min="0"
                        max="100"
                        step="0.01"
                        value={item.percentage}
                        onChange={(event) => updateItem(index, { percentage: event.target.value })}
                      />
                    </td>
                    <td>{((Number(targetWeight || 0) * Number(item.percentage || 0)) / 100).toFixed(3)}</td>
                    <td>
                      <button
                        className="button secondary-button"
                        type="button"
                        onClick={() => removeItem(index)}
                        disabled={form.items.length === 1}
                        aria-label="Quitar ingrediente"
                      >
                        <Trash2 size={16} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            </div>

            <p className={totalPercentage === 100 ? "muted" : "notice notice-error"}>
              Total: {formatPercent(totalPercentage)}% {totalPercentage === 100 ? "" : "La formula debe sumar 100%."}
            </p>

            <div className="row-actions">
              <button className="button secondary-button" type="button" onClick={addItem}>
                <Plus size={18} /> Agregar ingrediente
              </button>
              <button className="button" type="button" onClick={saveFormula} disabled={loading}>
                <Save size={18} /> {loading ? "Guardando..." : "Guardar formula"}
              </button>
            </div>
          </form>
        </section>

        <section className="panel">
          <h2>Formulas registradas</h2>
          <div className="formula-mobile-list mobile-only">
            {formulas.map((formula) => {
              const detail = detailFor(formula);
              const total = detail?.items.reduce((sum, item) => sum + Number(item.percentage), 0) ?? 0;
              return (
                <article className="mobile-record-card" key={formula.id}>
                  <div>
                    <strong>{formula.name}</strong>
                    <span>Version {formula.version} - {formula.status}</span>
                    <span>{detail?.items.length ?? "-"} ingredientes</span>
                    <span>Total: {formatPercent(total)}%</span>
                  </div>
                  <button className="button secondary-button" type="button" disabled={loading} onClick={() => selectFormula(formula)}>
                    Ver detalle
                  </button>
                </article>
              );
            })}
            {formulas.length === 0 ? <div className="empty-state">Todavia no hay formulas cargadas.</div> : null}
          </div>
          <div className="table-scroll desktop-table">
          <table className="table">
            <thead>
              <tr>
                <th>Nombre</th>
                <th>Version</th>
                <th>Estado</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {formulas.map((formula) => (
                <tr key={formula.id}>
                  <td>{formula.name}</td>
                  <td>{formula.version}</td>
                  <td>{formula.status}</td>
                  <td>
                    <button
                      className="button secondary-button"
                      type="button"
                      disabled={loading}
                      onClick={() => selectFormula(formula)}
                    >
                      Ver
                    </button>
                  </td>
                </tr>
              ))}
              {formulas.length === 0 ? (
                <tr>
                  <td colSpan={4} className="muted">
                    Todavia no hay formulas cargadas o la base de datos no esta disponible.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
          </div>
        </section>

        {selectedFormula ? (
          <section className="panel">
            <h2>
              {selectedFormula.name} v{selectedFormula.version}
            </h2>
            <p className="muted">
              Revisa los porcentajes importados y su equivalente en gramos para el peso que quieras controlar.
            </p>
            <div className="field">
              <label htmlFor="detailTargetWeight">Ver gramos para</label>
              <input
                id="detailTargetWeight"
                type="number"
                min="1"
                value={detailTargetWeight}
                onChange={(event) => setDetailTargetWeight(event.target.value)}
              />
            </div>
            <div className="formula-detail-cards mobile-only">
              {selectedFormula.items.map((item) => (
                <article className="mobile-record-card" key={item.ingredient_resource_id}>
                  <div>
                    <strong>{item.ingredient_name}</strong>
                    <span>{formatPercent(item.percentage)}%</span>
                    <span>
                      20 g: {((20 * Number(item.percentage || 0)) / 100).toLocaleString("es-UY", { maximumFractionDigits: 4 })} g
                    </span>
                  </div>
                  <div>
                    <strong>{stockFor(item.ingredient_resource_id)} g</strong>
                    <span>Stock disponible</span>
                  </div>
                </article>
              ))}
            </div>
            <div className="table-scroll desktop-table">
            <table className="table">
              <thead>
                <tr>
                  <th>Ingrediente</th>
                  <th>%</th>
                  <th>g calculados</th>
                </tr>
              </thead>
              <tbody>
                {selectedFormula.items.map((item) => (
                  <tr key={item.ingredient_resource_id}>
                    <td>{item.ingredient_name}</td>
                    <td>{formatPercent(item.percentage)}%</td>
                    <td>
                      {((Number(detailTargetWeight || 0) * Number(item.percentage || 0)) / 100).toLocaleString(
                        "es-UY",
                        { maximumFractionDigits: 4 },
                      )}{" "}
                      g
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            </div>
            <p className="muted">
              Total:{" "}
              {selectedFormula.items
                .reduce((sum, item) => sum + Number(item.percentage), 0)
                .toLocaleString("es-UY", { maximumFractionDigits: 2 })}
              %
            </p>
          </section>
        ) : null}
      </div>
    </AppShell>
  );
}
