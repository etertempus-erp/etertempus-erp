"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { CheckCircle2, Plus, ReceiptText, Save, Trash2 } from "lucide-react";

import { AppShell } from "@/components/AppShell";
import { apiGet, apiPost, ORGANIZATION_ID, PurchaseOptions, PurchaseRead, Resource, UnitType } from "@/lib/api";
import { friendlyErrorMessage } from "@/lib/messages";
import { useUnsavedChangesWarning } from "@/lib/useUnsavedChangesWarning";

type QuickPurchaseLine = {
  resource_id: string;
  resource_name: string;
  quantity: string;
  unit: UnitType;
  total_amount: string;
  unit_price: string;
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

export default function QuickPurchasePage() {
  const [resources, setResources] = useState<Resource[]>([]);
  const [options, setOptions] = useState<PurchaseOptions | null>(null);
  const [purchaseDate, setPurchaseDate] = useState(new Date().toISOString().slice(0, 10));
  const [supplierName, setSupplierName] = useState("");
  const [newSupplierName, setNewSupplierName] = useState("");
  const [receiptNumber, setReceiptNumber] = useState("");
  const [notes, setNotes] = useState("");
  const [resourceId, setResourceId] = useState("");
  const [quantity, setQuantity] = useState("1");
  const [totalAmount, setTotalAmount] = useState("");
  const [lines, setLines] = useState<QuickPurchaseLine[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const purchasableResources = resources.filter(
    (resource) => resource.active && ["raw_material", "packaging", "product"].includes(resource.type),
  );
  const selectedResource = purchasableResources.find((item) => item.id === resourceId);
  const supplierNameToSave = supplierName === "__new__" ? newSupplierName.trim() : supplierName.trim();
  const total = useMemo(() => lines.reduce((sum, line) => sum + numberValue(line.total_amount), 0), [lines]);
  const hasUnsavedChanges =
    lines.length > 0 ||
    Boolean(supplierName.trim()) ||
    Boolean(newSupplierName.trim()) ||
    Boolean(receiptNumber.trim()) ||
    Boolean(notes.trim()) ||
    Boolean(resourceId) ||
    quantity !== "1" ||
    Boolean(totalAmount);

  useUnsavedChangesWarning(hasUnsavedChanges && !saving);

  async function loadData() {
    try {
      setError(null);
      const [resourceData, optionData] = await Promise.all([
        apiGet<Resource[]>(`/resources?organization_id=${ORGANIZATION_ID}`),
        apiGet<PurchaseOptions>(`/purchases/options?organization_id=${ORGANIZATION_ID}`),
      ]);
      setResources(resourceData);
      setOptions(optionData);
    } catch (err) {
      setError(friendlyErrorMessage(err, "No se pudieron cargar los datos de compra."));
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  function addLine() {
    setError(null);
    setMessage(null);
    if (!selectedResource) return setError("Selecciona el recurso comprado.");
    if (numberValue(quantity) <= 0) return setError("La cantidad debe ser mayor a cero.");
    if (numberValue(totalAmount) < 0) return setError("El importe total no puede ser negativo.");
    const unitPrice = numberValue(quantity) > 0 ? numberValue(totalAmount) / numberValue(quantity) : 0;
    setLines((current) => [
      ...current,
      {
        resource_id: selectedResource.id,
        resource_name: selectedResource.name,
        quantity,
        unit: selectedResource.unit,
        total_amount: totalAmount || "0",
        unit_price: String(unitPrice),
      },
    ]);
    setResourceId("");
    setQuantity("1");
    setTotalAmount("");
  }

  async function save(confirm: boolean) {
    if (saving) return;
    setSaving(true);
    setError(null);
    setMessage(null);

    if (!purchaseDate) {
      setSaving(false);
      return setError("Selecciona la fecha de la compra.");
    }
    if (lines.length === 0) {
      setSaving(false);
      return setError("Agrega al menos un recurso comprado.");
    }

    try {
      const purchase = await apiPost<PurchaseRead>("/purchases", {
        organization_id: ORGANIZATION_ID,
        purchase_date: purchaseDate,
        supplier_name: supplierNameToSave || "Sin proveedor",
        receipt_number: receiptNumber.trim() || null,
        notes: notes.trim() || null,
        lines: lines.map((line) => ({
          resource_id: line.resource_id,
          quantity: Number(line.quantity),
          unit: line.unit,
          unit_price: Number(line.unit_price),
        })),
      });
      if (confirm) {
        const confirmed = await apiPost<PurchaseRead>(
          `/purchases/${purchase.id}/confirm?organization_id=${ORGANIZATION_ID}`,
          {},
        );
        setMessage(`Compra ${confirmed.code} confirmada. El stock fue actualizado.`);
      } else {
        setMessage(`Compra ${purchase.code} guardada como borrador. Todavia no modifica stock.`);
      }
      setLines([]);
      setSupplierName("");
      setNewSupplierName("");
      setReceiptNumber("");
      setNotes("");
    } catch (err) {
      setError(friendlyErrorMessage(err, "No se pudo guardar la compra. Los datos quedaron en pantalla."));
    } finally {
      setSaving(false);
    }
  }

  return (
    <AppShell>
      <section className="page-title">
        <div>
          <h1>Compra rapida</h1>
          <p>Registro tactil de compras desde el celular.</p>
        </div>
        <Link className="button secondary-button" href="/compras">
          Ver compras
        </Link>
      </section>

      <div className="stack mobile-operation">
        {message ? <div className="notice notice-ok">{message}</div> : null}
        {error ? <div className="notice notice-error">{error}</div> : null}

        <section className="panel">
          <div className="form">
            <label className="field">
              <span>Fecha</span>
              <input type="date" value={purchaseDate} onChange={(event) => setPurchaseDate(event.target.value)} />
            </label>
            <label className="field">
              <span>Proveedor opcional</span>
              <select value={supplierName} onChange={(event) => setSupplierName(event.target.value)}>
                <option value="">Sin proveedor</option>
                {options?.suppliers.map((supplier) => (
                  <option key={supplier.id} value={supplier.name}>
                    {supplier.name}
                  </option>
                ))}
                <option value="__new__">Agregar proveedor nuevo...</option>
              </select>
            </label>
            {supplierName === "__new__" ? (
              <label className="field">
                <span>Nuevo proveedor</span>
                <input value={newSupplierName} onChange={(event) => setNewSupplierName(event.target.value)} />
              </label>
            ) : null}
            <label className="field">
              <span>Comprobante opcional</span>
              <input value={receiptNumber} onChange={(event) => setReceiptNumber(event.target.value)} />
            </label>
            <label className="field">
              <span>Observacion opcional</span>
              <input value={notes} onChange={(event) => setNotes(event.target.value)} />
            </label>
          </div>
        </section>

        <section className="panel">
          <h2>Agregar recurso</h2>
          <div className="form">
            <label className="field">
              <span>Recurso</span>
              <select value={resourceId} onChange={(event) => setResourceId(event.target.value)}>
                <option value="">Seleccionar recurso</option>
                {purchasableResources.map((resource) => (
                  <option key={resource.id} value={resource.id}>
                    {resource.name} ({resource.unit})
                  </option>
                ))}
              </select>
            </label>
            <div className="quick-line-grid">
              <label className="field">
                <span>Cantidad</span>
                <input inputMode="decimal" type="number" min="0.001" step="0.001" value={quantity} onChange={(event) => setQuantity(event.target.value)} />
              </label>
              <label className="field">
                <span>Unidad</span>
                <input value={selectedResource?.unit ?? "-"} readOnly />
              </label>
            </div>
            <label className="field">
              <span>Importe total</span>
              <input inputMode="decimal" type="number" min="0" step="0.01" value={totalAmount} onChange={(event) => setTotalAmount(event.target.value)} />
            </label>
            <button className="button touch-button" type="button" onClick={addLine}>
              <Plus size={18} /> Agregar linea
            </button>
          </div>
        </section>

        <section className="panel">
          <h2>Lineas</h2>
          <div className="mobile-card-list">
            {lines.map((line, index) => (
              <article className="mobile-record-card" key={`${line.resource_id}-${index}`}>
                <div>
                  <strong>{line.resource_name}</strong>
                  <span>{line.quantity} {line.unit}</span>
                </div>
                <div>
                  <strong>{money(line.total_amount)}</strong>
                  <button className="button secondary-button icon-button" type="button" onClick={() => setLines((current) => current.filter((_, itemIndex) => itemIndex !== index))}>
                    <Trash2 size={16} />
                  </button>
                </div>
              </article>
            ))}
            {lines.length === 0 ? <div className="empty-state">Todavia no agregaste recursos.</div> : null}
          </div>
          <div className="sticky-mobile-total">
            <span>Total</span>
            <strong>{money(total)}</strong>
          </div>
          <div className="mobile-action-grid">
            <button className="button secondary-button touch-button" type="button" onClick={() => save(false)} disabled={saving}>
              <ReceiptText size={18} /> Guardar borrador
            </button>
            <button className="button touch-button" type="button" onClick={() => save(true)} disabled={saving}>
              <CheckCircle2 size={18} /> Guardar y confirmar
            </button>
          </div>
        </section>
      </div>
    </AppShell>
  );
}
