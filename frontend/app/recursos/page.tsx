"use client";

import { useEffect, useState } from "react";
import { PackageCheck, RefreshCw, Save, Search } from "lucide-react";

import { AppShell } from "@/components/AppShell";
import {
  apiGet,
  apiPost,
  apiPut,
  ORGANIZATION_ID,
  Resource,
  ResourceStock,
  ResourceType,
  UnitType,
} from "@/lib/api";
import { friendlyErrorMessage } from "@/lib/messages";

type ResourceForm = {
  code: string;
  name: string;
  type: ResourceType;
  unit: UnitType;
  minimum_stock: string;
  active: boolean;
};

const initialForm: ResourceForm = {
  code: "",
  name: "",
  type: "raw_material",
  unit: "g",
  minimum_stock: "0",
  active: true,
};

const resourceCodePrefixes: Record<ResourceType, string> = {
  raw_material: "MP",
  packaging: "PK",
  product: "PR",
  mix: "MX",
};

const resourceTypeLabels: Record<ResourceType, string> = {
  raw_material: "Materia prima",
  packaging: "Packaging",
  product: "Producto",
  mix: "Mezcla",
};

const unitLabels: Record<UnitType, string> = {
  g: "g",
  kg: "kg",
  ml: "ml",
  unit: "unidad",
};

function nextResourceCode(resources: Resource[], type: ResourceType) {
  const prefix = resourceCodePrefixes[type];
  const nextNumber =
    resources.reduce((maxNumber, resource) => {
      const match = resource.code.match(new RegExp(`^${prefix}-(\\d+)$`, "i"));
      return match ? Math.max(maxNumber, Number(match[1])) : maxNumber;
    }, 0) + 1;

  return `${prefix}-${String(nextNumber).padStart(4, "0")}`;
}

function removeAccents(value: string) {
  return value.normalize("NFD").replace(/[\u0300-\u036f]/g, "");
}

function normalized(value: string) {
  return removeAccents(value).toLowerCase().trim();
}

function resourceSortGroup(resource: Resource) {
  const name = normalized(resource.name);
  const isProduct = resource.type === "product";
  const isTopping = isProduct && (name.startsWith("topping ") || ["aire", "fuego", "agua", "tierra", "eter"].includes(name));
  const isCommercialAccessory =
    name.startsWith("box ") ||
    name.startsWith("kit ") ||
    name.includes("infusor") ||
    name.includes("sobre") ||
    name.includes("tote") ||
    name.includes("termo");

  if (isProduct && !isTopping && !isCommercialAccessory) return 1;
  if (isTopping) return 2;
  return 3;
}

export default function ResourcesPage() {
  const [form, setForm] = useState<ResourceForm>(initialForm);
  const [resources, setResources] = useState<Resource[]>([]);
  const [stockByResource, setStockByResource] = useState<Record<string, string>>({});
  const [resourceEdits, setResourceEdits] = useState<Record<string, ResourceForm>>({});
  const [stockEdits, setStockEdits] = useState<Record<string, string>>({});
  const [searchTerm, setSearchTerm] = useState("");
  const [typeFilter, setTypeFilter] = useState<ResourceType | "all">("all");
  const [statusFilter, setStatusFilter] = useState<"active" | "inactive" | "all">("active");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function loadResources() {
    try {
      setError(null);
      const [data, stockData] = await Promise.all([
        apiGet<Resource[]>(`/resources?organization_id=${ORGANIZATION_ID}`),
        apiGet<ResourceStock[]>(`/resources/stock?organization_id=${ORGANIZATION_ID}`),
      ]);
      setResources(data);
      setStockByResource(
        Object.fromEntries(stockData.map((stock) => [stock.resource_id, String(Number(stock.quantity))])),
      );
      setResourceEdits(
        Object.fromEntries(
          data.map((resource) => [
            resource.id,
            {
              code: resource.code,
              name: resource.name,
              type: resource.type,
              unit: resource.unit,
              minimum_stock: String(Number(resource.minimum_stock)),
              active: resource.active,
            },
          ]),
        ),
      );
      setStockEdits({});
    } catch (err) {
      setError(friendlyErrorMessage(err, "No se pudieron cargar los recursos."));
    }
  }

  useEffect(() => {
    loadResources();
  }, []);

  useEffect(() => {
    setForm((currentForm) => ({
      ...currentForm,
      code: nextResourceCode(resources, currentForm.type),
    }));
  }, [resources, form.type]);

  const filteredResources = resources
    .filter((resource) => {
      const matchesType = typeFilter === "all" || resource.type === typeFilter;
      const matchesStatus =
        statusFilter === "all" ||
        (statusFilter === "active" && resource.active) ||
        (statusFilter === "inactive" && !resource.active);
      const search = normalized(searchTerm);
      const matchesSearch =
        !search ||
        normalized(resource.name).includes(search) ||
        normalized(resource.code).includes(search);
      return matchesType && matchesStatus && matchesSearch;
    })
    .sort((a, b) => {
      const groupDifference = resourceSortGroup(a) - resourceSortGroup(b);
      if (groupDifference !== 0) return groupDifference;
      return normalized(a.name).localeCompare(normalized(b.name), "es");
    });

  async function saveResource() {
    setLoading(true);
    setMessage(null);
    setError(null);

    if (!form.name.trim()) {
      setError("Escribe el nombre del recurso antes de guardar. El codigo se completa automaticamente.");
      setLoading(false);
      return;
    }

    if (Number(form.minimum_stock || 0) < 0) {
      setError("El stock minimo no puede ser negativo. Escribe 0 o una cantidad mayor.");
      setLoading(false);
      return;
    }

    if (resources.some((resource) => resource.code.toLowerCase() === form.code.trim().toLowerCase())) {
      setError(
        "Ese codigo ya existe. Si querias cambiar el stock minimo, usa la tabla de recursos registrados. Si estas creando algo nuevo, elige otro codigo.",
      );
      setLoading(false);
      return;
    }

    try {
      await apiPost("/resources", {
        organization_id: ORGANIZATION_ID,
        ...form,
        code: nextResourceCode(resources, form.type),
        name: removeAccents(form.name.trim()),
        minimum_stock: Number(form.minimum_stock || 0),
      });
      setForm(initialForm);
      setMessage("Recurso guardado.");
      await loadResources();
    } catch (err) {
      setError(friendlyErrorMessage(err, "No se pudo guardar el recurso."));
    } finally {
      setLoading(false);
    }
  }

  function updateResourceEdit(resource: Resource, edit: Partial<ResourceForm>) {
    const currentEdit = resourceEdits[resource.id] ?? {
      code: resource.code,
      name: resource.name,
      type: resource.type,
      unit: resource.unit,
      minimum_stock: String(Number(resource.minimum_stock)),
      active: resource.active,
    };

    setResourceEdits({
      ...resourceEdits,
      [resource.id]: {
        ...currentEdit,
        ...edit,
      },
    });
  }

  async function updateResource(resource: Resource) {
    setLoading(true);
    setMessage(null);
    setError(null);

    const edit = resourceEdits[resource.id];
    if (!edit) {
      setError("No encontre los datos editables de este recurso. Actualiza la pantalla e intenta de nuevo.");
      setLoading(false);
      return;
    }

    if (!edit.name.trim()) {
      setError("El recurso necesita un nombre antes de guardar.");
      setLoading(false);
      return;
    }

    if (Number(edit.minimum_stock || 0) < 0) {
      setError("El stock minimo no puede ser negativo. Escribe 0 o una cantidad mayor.");
      setLoading(false);
      return;
    }

    try {
      await apiPut(`/resources/${resource.id}?organization_id=${ORGANIZATION_ID}`, {
        code: edit.code,
        name: removeAccents(edit.name.trim()),
        type: edit.type,
        unit: edit.unit,
        minimum_stock: Number(edit.minimum_stock || 0),
        active: edit.active,
      });
      setMessage(
        `Recurso actualizado: ${removeAccents(edit.name.trim())} (${edit.active ? "activo" : "inactivo"}).`,
      );
      await loadResources();
    } catch (err) {
      setError(friendlyErrorMessage(err, "No se pudo actualizar el recurso."));
    } finally {
      setLoading(false);
    }
  }

  async function updateCurrentStock(resource: Resource) {
    setLoading(true);
    setMessage(null);
    setError(null);

    const rawQuantity = stockEdits[resource.id];
    if (rawQuantity === undefined || rawQuantity === "") {
      setError("Escribe el stock actual que quieres dejar registrado.");
      setLoading(false);
      return;
    }

    const quantity = Number(rawQuantity);
    if (quantity < 0) {
      setError("El stock actual no puede ser negativo. Escribe 0 o una cantidad mayor.");
      setLoading(false);
      return;
    }

    try {
      const response = await apiPost<{ previous_quantity: string; new_quantity: string; adjustment: string }>(
        `/resources/${resource.id}/stock`,
        {
        organization_id: ORGANIZATION_ID,
        quantity,
        unit: resource.unit,
        reason: "Actualizacion manual de stock actual",
        },
      );
      setMessage(
        `Stock actualizado para ${resource.name}: antes ${Number(response.previous_quantity).toLocaleString("es-UY")}, ahora ${Number(response.new_quantity).toLocaleString("es-UY")}.`,
      );
      await loadResources();
    } catch (err) {
      setError(friendlyErrorMessage(err, "No se pudo actualizar el stock."));
    } finally {
      setLoading(false);
    }
  }

  return (
    <AppShell>
      <section className="page-title">
        <div>
          <h1>Recursos</h1>
          <p>Alta inicial de materias primas, packaging y productos.</p>
        </div>
        <button className="button secondary-button" type="button" onClick={loadResources}>
          <RefreshCw size={18} /> Actualizar
        </button>
      </section>

      <div className="stack">
        {message ? <div className="notice notice-ok">{message}</div> : null}
        {error ? <div className="notice notice-error">{error}</div> : null}

        <section className="panel">
          <h2>Nuevo recurso</h2>
          <p className="muted">
            Escribe el nombre y el sistema asigna el codigo automaticamente. Para cambiar el stock minimo de uno
            existente, editalo en la tabla de abajo.
          </p>
          <form className="form" onSubmit={(event) => event.preventDefault()}>
            <div className="field">
              <label htmlFor="code">Codigo automatico</label>
              <input
                id="code"
                readOnly
                value={form.code}
              />
            </div>
            <div className="field">
              <label htmlFor="name">Nombre</label>
              <input
                id="name"
                placeholder="Te negro Ceylan"
                value={form.name}
                onChange={(event) => setForm({ ...form, name: event.target.value })}
              />
            </div>
            <div className="field">
              <label htmlFor="type">Tipo</label>
              <select
                id="type"
                value={form.type}
                onChange={(event) => {
                  const type = event.target.value as ResourceType;
                  setForm({ ...form, type, code: nextResourceCode(resources, type) });
                }}
              >
                <option value="raw_material">Materia prima</option>
                <option value="packaging">Packaging</option>
                <option value="product">Producto</option>
                <option value="mix">Mezcla</option>
              </select>
            </div>
            <div className="field">
              <label htmlFor="unit">Unidad</label>
              <select
                id="unit"
                value={form.unit}
                onChange={(event) => setForm({ ...form, unit: event.target.value as UnitType })}
              >
                <option value="g">g</option>
                <option value="kg">kg</option>
                <option value="ml">ml</option>
                <option value="unit">unidad</option>
              </select>
            </div>
            <div className="field">
              <label htmlFor="minimum_stock">Stock minimo</label>
              <input
                id="minimum_stock"
                type="number"
                min="0"
                value={form.minimum_stock}
                onChange={(event) => setForm({ ...form, minimum_stock: event.target.value })}
              />
            </div>
            <button className="button" type="button" onClick={saveResource} disabled={loading}>
              <Save size={18} /> {loading ? "Guardando..." : "Guardar recurso"}
            </button>
          </form>
        </section>

        <section className="panel">
          <h2>Recursos registrados</h2>
          <div className="resource-toolbar">
            <label className="search-field">
              <Search size={18} />
              <input
                value={searchTerm}
                placeholder="Buscar por nombre o codigo"
                onChange={(event) => setSearchTerm(event.target.value)}
              />
            </label>
            <select
              className="compact-select"
              value={typeFilter}
              onChange={(event) => setTypeFilter(event.target.value as ResourceType | "all")}
            >
              <option value="all">Todos los tipos</option>
              <option value="raw_material">Materia prima</option>
              <option value="packaging">Packaging</option>
              <option value="product">Producto</option>
              <option value="mix">Mezcla</option>
            </select>
            <select
              className="compact-select"
              value={statusFilter}
              onChange={(event) => setStatusFilter(event.target.value as "active" | "inactive" | "all")}
            >
              <option value="active">Activos</option>
              <option value="inactive">Inactivos</option>
              <option value="all">Todos</option>
            </select>
          </div>

          <div className="resource-list">
            {filteredResources.map((resource) => {
              const edit = resourceEdits[resource.id] ?? {
                code: resource.code,
                name: resource.name,
                type: resource.type,
                unit: resource.unit,
                minimum_stock: String(Number(resource.minimum_stock)),
                active: resource.active,
              };
              const currentStock = Number(stockByResource[resource.id] ?? 0);

              return (
                <article className={edit.active ? "resource-card" : "resource-card resource-card-inactive"} key={resource.id}>
                  <header className="resource-card-header">
                    <div>
                      <div className="resource-code">
                        {edit.code}
                        <span className={edit.active ? "status-dot status-active" : "status-dot status-inactive"}>
                          {edit.active ? "Activo" : "Inactivo"}
                        </span>
                      </div>
                      <input
                        className="resource-name-input"
                        value={edit.name}
                        onChange={(event) => updateResourceEdit(resource, { name: event.target.value })}
                        aria-label="Nombre del recurso"
                      />
                    </div>
                    <div className="stock-pill">
                      <PackageCheck size={18} />
                      <span>{currentStock.toLocaleString("es-UY", { maximumFractionDigits: 3 })}</span>
                      <small>{unitLabels[resource.unit]}</small>
                    </div>
                  </header>

                  <div className="resource-card-grid">
                    <label className="field compact-field">
                      <span>Tipo</span>
                      <select
                        value={edit.type}
                        onChange={(event) => {
                          const type = event.target.value as ResourceType;
                          updateResourceEdit(resource, {
                            type,
                            code: type === resource.type ? resource.code : nextResourceCode(resources, type),
                          });
                        }}
                      >
                        <option value="raw_material">Materia prima</option>
                        <option value="packaging">Packaging</option>
                        <option value="product">Producto</option>
                        <option value="mix">Mezcla</option>
                      </select>
                    </label>

                    <label className="field compact-field">
                      <span>Unidad</span>
                      <select
                        value={edit.unit}
                        onChange={(event) => updateResourceEdit(resource, { unit: event.target.value as UnitType })}
                      >
                        <option value="g">g</option>
                        <option value="kg">kg</option>
                        <option value="ml">ml</option>
                        <option value="unit">unidad</option>
                      </select>
                    </label>

                    <label className="field compact-field">
                      <span>Stock minimo</span>
                      <input
                        type="number"
                        min="0"
                        value={edit.minimum_stock}
                        onChange={(event) => updateResourceEdit(resource, { minimum_stock: event.target.value })}
                      />
                    </label>

                    <label className="field compact-field">
                      <span>Stock actual</span>
                      <input
                        type="number"
                        min="0"
                        value={stockEdits[resource.id] ?? ""}
                        placeholder={stockByResource[resource.id] ?? "0"}
                        onChange={(event) =>
                          setStockEdits({
                            ...stockEdits,
                            [resource.id]: event.target.value,
                          })
                        }
                      />
                    </label>

                    <label className="field compact-field">
                      <span>Estado</span>
                      <select
                        value={edit.active ? "active" : "inactive"}
                        onChange={(event) =>
                          updateResourceEdit(resource, { active: event.target.value === "active" })
                        }
                      >
                        <option value="active">Activo</option>
                        <option value="inactive">Inactivo</option>
                      </select>
                    </label>
                  </div>

                  <footer className="resource-card-footer">
                    <div className="resource-meta">
                      <span>{resourceTypeLabels[resource.type]}</span>
                      <span>Costo {resource.latest_unit_cost ? `$${Number(resource.latest_unit_cost).toFixed(2)}` : "-"}</span>
                      <span>Proveedor {resource.latest_supplier_name || "-"}</span>
                    </div>
                    <div className="row-actions">
                      <button
                        className="button secondary-button"
                        type="button"
                        disabled={loading}
                        onClick={() => updateResource(resource)}
                      >
                        <Save size={16} /> Guardar
                      </button>
                      <button
                        className="button"
                        type="button"
                        disabled={loading}
                        onClick={() => updateCurrentStock(resource)}
                      >
                        Actualizar stock
                      </button>
                    </div>
                  </footer>
                </article>
              );
            })}
            {filteredResources.length === 0 ? (
              <div className="empty-state">No hay recursos para esa busqueda.</div>
            ) : null}
          </div>
        </section>
      </div>
    </AppShell>
  );
}
