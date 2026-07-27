"use client";

import { useEffect, useMemo, useState } from "react";
import { CheckCircle2, Eye, Plus, ReceiptText, RefreshCw, Trash2, XCircle } from "lucide-react";

import { AppShell } from "@/components/AppShell";
import { apiGet, apiPost, ORGANIZATION_ID, PurchaseOptions, PurchaseRead, Resource, UnitType } from "@/lib/api";
import { friendlyErrorMessage } from "@/lib/messages";

type PurchaseLineDraft = {
  resource_id: string;
  resource_name: string;
  quantity: string;
  unit: UnitType;
  unit_price: string;
  purchase_price: string;
};

function money(value: string | number) {
  return Number(value || 0).toLocaleString("es-UY", {
    maximumFractionDigits: 2,
    style: "currency",
    currency: "UYU",
  });
}

function numberValue(value: string) {
  return Number(value || 0);
}

function statusLabel(status: PurchaseRead["status"]) {
  if (status === "confirmed") return "Confirmada";
  if (status === "cancelled") return "Anulada";
  return "Borrador";
}

function priceInputLabel(resource: Resource | undefined) {
  if (!resource) return "Precio de compra";
  if (resource.unit === "g") return "Precio por kilo";
  if (resource.unit === "kg") return "Precio por kilo";
  if (resource.unit === "ml") return "Precio por ml";
  return "Precio por unidad";
}

function unitCostFromPurchasePrice(resource: Resource, price: number) {
  if (resource.unit === "g") return price / 1000;
  return price;
}

function displayPurchasePrice(unit: UnitType, unitPrice: string | number) {
  const value = Number(unitPrice || 0);
  if (unit === "g") return `${money(value * 1000)} / kg`;
  if (unit === "kg") return `${money(value)} / kg`;
  if (unit === "ml") return `${money(value)} / ml`;
  return `${money(value)} / unidad`;
}

export default function PurchasesPage() {
  const [resources, setResources] = useState<Resource[]>([]);
  const [purchaseOptions, setPurchaseOptions] = useState<PurchaseOptions | null>(null);
  const [purchases, setPurchases] = useState<PurchaseRead[]>([]);
  const [selectedPurchase, setSelectedPurchase] = useState<PurchaseRead | null>(null);

  const [purchaseDate, setPurchaseDate] = useState(new Date().toISOString().slice(0, 10));
  const [supplierName, setSupplierName] = useState("");
  const [newSupplierName, setNewSupplierName] = useState("");
  const [receiptNumber, setReceiptNumber] = useState("");
  const [notes, setNotes] = useState("");
  const [resourceId, setResourceId] = useState("");
  const [quantity, setQuantity] = useState("1");
  const [unitPrice, setUnitPrice] = useState("0");
  const [lines, setLines] = useState<PurchaseLineDraft[]>([]);
  const [statusFilter, setStatusFilter] = useState("");

  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const purchasableResources = resources.filter(
    (resource) => resource.active && ["raw_material", "packaging", "product"].includes(resource.type),
  );
  const selectedResource = resources.find((item) => item.id === resourceId);
  const supplierNameToSave = supplierName === "__new__" ? newSupplierName.trim() : supplierName.trim();

  const total = useMemo(
    () => lines.reduce((sum, line) => sum + numberValue(line.quantity) * numberValue(line.unit_price), 0),
    [lines],
  );

  async function loadData() {
    try {
      setError(null);
      const [resourceData, purchaseData, optionData] = await Promise.all([
        apiGet<Resource[]>(`/resources?organization_id=${ORGANIZATION_ID}`),
        apiGet<PurchaseRead[]>(`/purchases?organization_id=${ORGANIZATION_ID}${statusFilter ? `&status=${statusFilter}` : ""}`),
        apiGet<PurchaseOptions>(`/purchases/options?organization_id=${ORGANIZATION_ID}`),
      ]);
      setResources(resourceData);
      setPurchases(purchaseData);
      setPurchaseOptions(optionData);
    } catch (err) {
      setError(friendlyErrorMessage(err, "No se pudieron cargar las compras."));
    }
  }

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter]);

  function addLine() {
    setMessage(null);
    setError(null);
    const resource = resources.find((item) => item.id === resourceId);
    if (!resource) {
      setError("Selecciona un recurso antes de agregarlo a la compra.");
      return;
    }
    if (numberValue(quantity) <= 0) {
      setError("La cantidad debe ser mayor a cero. No se permiten numeros negativos.");
      return;
    }
    const enteredPrice = numberValue(unitPrice);
    if (enteredPrice < 0) {
      setError("El precio unitario no puede ser negativo.");
      return;
    }
    const unitCost = unitCostFromPurchasePrice(resource, enteredPrice);
    setLines((current) => [
      ...current,
      {
        resource_id: resource.id,
        resource_name: resource.name,
        quantity,
        unit: resource.unit,
        unit_price: String(unitCost),
        purchase_price: unitPrice || "0",
      },
    ]);
    setResourceId("");
    setQuantity("1");
    setUnitPrice("0");
  }

  async function saveDraft() {
    setLoading(true);
    setMessage(null);
    setError(null);

    if (!purchaseDate) {
      setError("Selecciona la fecha de la compra.");
      setLoading(false);
      return null;
    }
    if (!supplierNameToSave) {
      setError("Selecciona un proveedor o carga uno nuevo antes de guardar la compra.");
      setLoading(false);
      return null;
    }
    if (lines.length === 0) {
      setError("Agrega al menos un recurso a la compra.");
      setLoading(false);
      return null;
    }

    try {
      const purchase = await apiPost<PurchaseRead>("/purchases", {
        organization_id: ORGANIZATION_ID,
        purchase_date: purchaseDate,
        supplier_name: supplierNameToSave,
        receipt_number: receiptNumber.trim() || null,
        notes: notes.trim() || null,
        lines: lines.map((line) => ({
          resource_id: line.resource_id,
          quantity: Number(line.quantity),
          unit: line.unit,
          unit_price: Number(line.unit_price),
        })),
      });
      setMessage(`Compra ${purchase.code} guardada como borrador. Todavia no modifica stock.`);
      setSelectedPurchase(purchase);
      await loadData();
      return purchase;
    } catch (err) {
      setError(friendlyErrorMessage(err, "No se pudo guardar la compra."));
      return null;
    } finally {
      setLoading(false);
    }
  }

  async function saveAndConfirm() {
    const purchase = await saveDraft();
    if (!purchase) return;
    await confirmPurchase(purchase.id);
      setLines([]);
      setSupplierName("");
      setNewSupplierName("");
      setReceiptNumber("");
      setNotes("");
  }

  async function confirmPurchase(purchaseId: string) {
    setLoading(true);
    setMessage(null);
    setError(null);
    try {
      const purchase = await apiPost<PurchaseRead>(
        `/purchases/${purchaseId}/confirm?organization_id=${ORGANIZATION_ID}`,
        {},
      );
      setMessage(`Compra ${purchase.code} confirmada. El stock fue actualizado.`);
      setSelectedPurchase(purchase);
      await loadData();
    } catch (err) {
      setError(friendlyErrorMessage(err, "No se pudo confirmar la compra. No se actualizo stock."));
    } finally {
      setLoading(false);
    }
  }

  async function cancelPurchase(purchase: PurchaseRead) {
    const reason = window.prompt(
      purchase.status === "confirmed"
        ? "Motivo de la anulacion. El sistema descontara del stock lo que habia ingresado esta compra."
        : "Motivo de la anulacion. Esta compra no modificaba stock porque estaba en borrador.",
      "",
    );
    if (reason === null) return;

    setLoading(true);
    setMessage(null);
    setError(null);
    try {
      const cancelled = await apiPost<PurchaseRead>(
        `/purchases/${purchase.id}/cancel?organization_id=${ORGANIZATION_ID}`,
        { reason },
      );
      setMessage(
        cancelled.movements.some((movement) => movement.type === "purchase_cancellation")
          ? `Compra ${cancelled.code} anulada. El stock fue ajustado.`
          : `Compra ${cancelled.code} anulada. No modificaba stock.`,
      );
      setSelectedPurchase(cancelled);
      await loadData();
    } catch (err) {
      setError(friendlyErrorMessage(err, "No se pudo anular la compra."));
    } finally {
      setLoading(false);
    }
  }

  async function openPurchase(purchaseId: string) {
    try {
      setError(null);
      const purchase = await apiGet<PurchaseRead>(`/purchases/${purchaseId}?organization_id=${ORGANIZATION_ID}`);
      setSelectedPurchase(purchase);
    } catch (err) {
      setError(friendlyErrorMessage(err, "No se pudo abrir el detalle de la compra."));
    }
  }

  return (
    <AppShell>
      <section className="page-title">
        <div>
          <h1>Compras</h1>
          <p>Registra compras y confirma entradas de stock.</p>
        </div>
        <button className="button secondary-button" type="button" onClick={loadData}>
          <RefreshCw size={18} /> Actualizar
        </button>
      </section>

      <div className="stack">
        {message ? <div className="notice notice-ok">{message}</div> : null}
        {error ? <div className="notice notice-error">{error}</div> : null}

        <section className="panel">
          <h2>Nueva compra</h2>
          <div className="form wide-form">
            <div className="form-grid">
              <div className="field">
                <label>Fecha</label>
                <input type="date" value={purchaseDate} onChange={(event) => setPurchaseDate(event.target.value)} />
              </div>
              <div className="field">
                <label>Proveedor</label>
                <select value={supplierName} onChange={(event) => setSupplierName(event.target.value)}>
                  <option value="">Seleccionar proveedor</option>
                  {purchaseOptions?.suppliers.map((supplier) => (
                    <option key={supplier.id} value={supplier.name}>
                      {supplier.name}
                    </option>
                  ))}
                  <option value="__new__">Agregar proveedor nuevo...</option>
                </select>
              </div>
              {supplierName === "__new__" ? (
                <div className="field">
                  <label>Nombre del nuevo proveedor</label>
                  <input
                    value={newSupplierName}
                    onChange={(event) => setNewSupplierName(event.target.value)}
                    placeholder="Ejemplo: Niter"
                  />
                </div>
              ) : null}
              <div className="field">
                <label>Comprobante opcional</label>
                <input value={receiptNumber} onChange={(event) => setReceiptNumber(event.target.value)} />
              </div>
              <div className="field">
                <label>Observaciones</label>
                <input value={notes} onChange={(event) => setNotes(event.target.value)} />
              </div>
            </div>

            <div className="line-builder purchase-line-builder">
              <div className="field">
                <label>Recurso</label>
                <select value={resourceId} onChange={(event) => setResourceId(event.target.value)}>
                  <option value="">Seleccionar recurso</option>
                  {purchasableResources.map((resource) => (
                    <option key={resource.id} value={resource.id}>
                      {resource.name} ({resource.unit})
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label>Cantidad</label>
                <input type="number" min="0.001" step="0.001" value={quantity} onChange={(event) => setQuantity(event.target.value)} />
              </div>
              <div className="field">
                <label>{priceInputLabel(selectedResource)}</label>
                <input type="number" min="0" step="0.0001" value={unitPrice} onChange={(event) => setUnitPrice(event.target.value)} />
              </div>
              <button className="button" type="button" onClick={addLine}>
                <Plus size={18} /> Agregar
              </button>
            </div>

            <div className="table-scroll">
            <table className="table">
              <thead>
                <tr>
                  <th>Recurso</th>
                  <th>Cantidad</th>
                  <th>Unidad</th>
                  <th>Precio de compra</th>
                  <th>Costo ERP</th>
                  <th>Subtotal</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {lines.map((line, index) => (
                  <tr key={`${line.resource_id}-${index}`}>
                    <td>{line.resource_name}</td>
                    <td>{line.quantity}</td>
                    <td>{line.unit}</td>
                    <td>{line.unit === "g" ? `${money(line.purchase_price)} / kg` : displayPurchasePrice(line.unit, line.unit_price)}</td>
                    <td>{money(line.unit_price)} / {line.unit}</td>
                    <td>{money(numberValue(line.quantity) * numberValue(line.unit_price))}</td>
                    <td>
                      <button
                        className="button secondary-button icon-button"
                        type="button"
                        aria-label="Quitar linea"
                        onClick={() => setLines((current) => current.filter((_, itemIndex) => itemIndex !== index))}
                      >
                        <Trash2 size={16} />
                      </button>
                    </td>
                  </tr>
                ))}
                {lines.length === 0 ? (
                  <tr>
                    <td className="muted" colSpan={7}>
                      Agrega recursos para guardar la compra.
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
            </div>

            <div className="sale-total">
              <span>Total</span>
              <strong>{money(total)}</strong>
            </div>

            <div className="row-actions">
              <button className="button secondary-button" type="button" onClick={saveDraft} disabled={loading}>
                <ReceiptText size={18} /> Guardar borrador
              </button>
              <button className="button" type="button" onClick={saveAndConfirm} disabled={loading}>
                <CheckCircle2 size={18} /> Confirmar compra
              </button>
            </div>
          </div>
        </section>

        <section className="panel">
          <h2>Listado de compras</h2>
          <div className="resource-toolbar">
            <select className="compact-select" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
              <option value="">Todas</option>
              <option value="draft">Borradores</option>
              <option value="confirmed">Confirmadas</option>
              <option value="cancelled">Anuladas</option>
            </select>
          </div>
          <div className="table-scroll">
          <table className="table">
            <thead>
              <tr>
                <th>Fecha</th>
                <th>Codigo</th>
                <th>Proveedor</th>
                <th>Comprobante</th>
                <th>Total</th>
                <th>Estado</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {purchases.map((purchase) => (
                <tr key={purchase.id}>
                  <td>{purchase.purchase_date}</td>
                  <td>{purchase.code}</td>
                  <td>{purchase.supplier_name}</td>
                  <td>{purchase.receipt_number ?? "-"}</td>
                  <td>{money(purchase.total)}</td>
                  <td>{statusLabel(purchase.status)}</td>
                  <td>
                    <div className="row-actions">
                      <button className="button secondary-button icon-button" type="button" onClick={() => openPurchase(purchase.id)} aria-label="Ver detalle">
                        <Eye size={16} />
                      </button>
                      {purchase.status === "draft" ? (
                        <button className="button secondary-button" type="button" onClick={() => confirmPurchase(purchase.id)}>
                          Confirmar
                        </button>
                      ) : null}
                      {purchase.status !== "cancelled" ? (
                        <button className="button secondary-button" type="button" onClick={() => cancelPurchase(purchase)}>
                          <XCircle size={16} /> Anular
                        </button>
                      ) : null}
                    </div>
                  </td>
                </tr>
              ))}
              {purchases.length === 0 ? (
                <tr>
                  <td className="muted" colSpan={7}>
                    Todavia no hay compras registradas.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
          </div>
        </section>

        {selectedPurchase ? (
          <section className="panel">
            <h2>Detalle {selectedPurchase.code}</h2>
            <p className="muted">
              {selectedPurchase.status === "confirmed"
                ? "Compra confirmada con movimientos de inventario."
                : selectedPurchase.status === "cancelled"
                  ? "Compra anulada. Se conserva el historial y no puede editarse."
                  : "Borrador: todavia no modifica stock."}
            </p>
            {selectedPurchase.cancellation_reason ? (
              <p className="muted">Motivo de anulacion: {selectedPurchase.cancellation_reason}</p>
            ) : null}
            <div className="table-scroll">
            <table className="table">
              <thead>
                <tr>
                  <th>Recurso</th>
                  <th>Cantidad</th>
                  <th>Unidad</th>
                  <th>Precio unitario</th>
                  <th>Costo ERP</th>
                  <th>Subtotal</th>
                </tr>
              </thead>
              <tbody>
                {selectedPurchase.lines.map((line) => (
                  <tr key={line.id}>
                    <td>{line.resource_name}</td>
                    <td>{line.quantity}</td>
                    <td>{line.unit}</td>
                    <td>{displayPurchasePrice(line.unit, line.unit_price)}</td>
                    <td>{money(line.unit_price)} / {line.unit}</td>
                    <td>{money(line.line_total)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            </div>
            {selectedPurchase.movements.length > 0 ? (
              <>
                <h2>Movimientos generados</h2>
                <div className="table-scroll">
                <table className="table">
                  <tbody>
                    {selectedPurchase.movements.map((movement) => (
                      <tr key={movement.id}>
                        <td>{movement.resource_name}</td>
                        <td>{movement.type}</td>
                        <td>{movement.quantity}</td>
                        <td>{movement.unit_cost_snapshot ? money(movement.unit_cost_snapshot) : "-"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                </div>
              </>
            ) : null}
          </section>
        ) : null}
      </div>
    </AppShell>
  );
}
