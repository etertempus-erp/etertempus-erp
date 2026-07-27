"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { Plus, ShoppingCart, Trash2 } from "lucide-react";

import { AppShell } from "@/components/AppShell";
import { apiGet, apiPost, ORGANIZATION_ID, ProductForSale, SaleOptions, SaleRead } from "@/lib/api";
import { friendlyErrorMessage } from "@/lib/messages";
import { useUnsavedChangesWarning } from "@/lib/useUnsavedChangesWarning";

type QuickSaleLine = {
  product_resource_id: string;
  product_name: string;
  quantity: string;
  unit_price: string;
  discount: string;
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

export default function QuickSalePage() {
  const [options, setOptions] = useState<SaleOptions | null>(null);
  const [products, setProducts] = useState<ProductForSale[]>([]);
  const [saleDate, setSaleDate] = useState(new Date().toISOString().slice(0, 10));
  const [channelId, setChannelId] = useState("");
  const [pointOfSaleId, setPointOfSaleId] = useState("");
  const [paymentMethodId, setPaymentMethodId] = useState("");
  const [notes, setNotes] = useState("");
  const [productId, setProductId] = useState("");
  const [quantity, setQuantity] = useState("1");
  const [unitPrice, setUnitPrice] = useState("");
  const [discount, setDiscount] = useState("0");
  const [lines, setLines] = useState<QuickSaleLine[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const selectedProduct = products.find((item) => item.id === productId);
  const selectedChannel = options?.channels.find((item) => item.id === channelId);
  const needsPointOfSale = selectedChannel
    ? selectedChannel.name.toLowerCase().includes("feria") || selectedChannel.name.toLowerCase().includes("punto")
    : false;
  const total = useMemo(
    () => lines.reduce((sum, line) => sum + Math.max(numberValue(line.quantity) * numberValue(line.unit_price) - numberValue(line.discount), 0), 0),
    [lines],
  );
  const hasUnsavedChanges =
    lines.length > 0 ||
    Boolean(notes.trim()) ||
    Boolean(productId) ||
    quantity !== "1" ||
    Boolean(unitPrice) ||
    discount !== "0";

  useUnsavedChangesWarning(hasUnsavedChanges && !saving);

  async function loadData() {
    try {
      setError(null);
      const [optionData, productData] = await Promise.all([
        apiGet<SaleOptions>(`/sales/options?organization_id=${ORGANIZATION_ID}`),
        apiGet<ProductForSale[]>(`/sales/products/available-for-sale?organization_id=${ORGANIZATION_ID}`),
      ]);
      setOptions(optionData);
      setProducts(productData);
      setChannelId((current) => current || optionData.channels[0]?.id || "");
      setPaymentMethodId((current) => current || optionData.payment_methods[0]?.id || "");
    } catch (err) {
      setError(friendlyErrorMessage(err, "No se pudieron cargar los datos de venta."));
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  function onProductChange(nextProductId: string) {
    setProductId(nextProductId);
    const product = products.find((item) => item.id === nextProductId);
    setUnitPrice(product?.suggested_price ?? "");
  }

  function addLine() {
    setError(null);
    setMessage(null);
    if (!selectedProduct) return setError("Selecciona un producto.");
    if (numberValue(quantity) <= 0) return setError("La cantidad debe ser mayor a cero.");
    if (numberValue(unitPrice) < 0 || numberValue(discount) < 0) return setError("Precio y descuento no pueden ser negativos.");
    if (numberValue(discount) > numberValue(quantity) * numberValue(unitPrice)) return setError("El descuento no puede superar el subtotal.");
    setLines((current) => [
      ...current,
      {
        product_resource_id: selectedProduct.id,
        product_name: selectedProduct.name,
        quantity,
        unit_price: unitPrice || "0",
        discount: discount || "0",
      },
    ]);
    setProductId("");
    setQuantity("1");
    setUnitPrice("");
    setDiscount("0");
  }

  async function saveSale() {
    if (saving) return;
    setSaving(true);
    setError(null);
    setMessage(null);
    if (!saleDate) {
      setSaving(false);
      return setError("Selecciona la fecha.");
    }
    if (!channelId) {
      setSaving(false);
      return setError("Selecciona el canal de venta.");
    }
    if (needsPointOfSale && !pointOfSaleId) {
      setSaving(false);
      return setError("Selecciona el punto de venta para este canal.");
    }
    if (!paymentMethodId) {
      setSaving(false);
      return setError("Selecciona el medio de pago.");
    }
    if (lines.length === 0) {
      setSaving(false);
      return setError("Agrega al menos un producto.");
    }

    try {
      const response = await apiPost<{ sale: SaleRead }>("/sales", {
        organization_id: ORGANIZATION_ID,
        sale_date: saleDate,
        channel_id: channelId,
        point_of_sale_id: needsPointOfSale ? pointOfSaleId || null : null,
        payment_method_id: paymentMethodId,
        customer_name: null,
        notes: notes.trim() || null,
        lines: lines.map((line) => ({
          product_resource_id: line.product_resource_id,
          quantity: Number(line.quantity),
          unit_price: Number(line.unit_price),
          discount: Number(line.discount || 0),
        })),
      });
      setMessage(`Venta ${response.sale.code} registrada. Stock descontado.`);
      setLines([]);
      setNotes("");
      const productData = await apiGet<ProductForSale[]>(`/sales/products/available-for-sale?organization_id=${ORGANIZATION_ID}`);
      setProducts(productData);
    } catch (err) {
      setError(friendlyErrorMessage(err, "La venta no pudo registrarse. No se desconto stock."));
    } finally {
      setSaving(false);
    }
  }

  return (
    <AppShell>
      <section className="page-title">
        <div>
          <h1>Venta rapida</h1>
          <p>Registra una venta desde el celular en pocos pasos.</p>
        </div>
        <Link className="button secondary-button" href="/ventas">
          Ver ventas
        </Link>
      </section>

      <div className="stack mobile-operation">
        {message ? <div className="notice notice-ok">{message}</div> : null}
        {error ? <div className="notice notice-error">{error}</div> : null}

        <section className="panel form">
          <label className="field">
            <span>Fecha</span>
            <input type="date" value={saleDate} onChange={(event) => setSaleDate(event.target.value)} />
          </label>
          <label className="field">
            <span>Canal</span>
            <select value={channelId} onChange={(event) => setChannelId(event.target.value)}>
              <option value="">Seleccionar canal</option>
              {options?.channels.map((channel) => (
                <option key={channel.id} value={channel.id}>{channel.name}</option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Punto de venta</span>
            <select value={pointOfSaleId} onChange={(event) => setPointOfSaleId(event.target.value)} disabled={!needsPointOfSale}>
              <option value="">{needsPointOfSale ? "Seleccionar punto" : "No corresponde"}</option>
              {options?.points_of_sale.map((point) => (
                <option key={point.id} value={point.id}>{point.name}</option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Medio de pago</span>
            <select value={paymentMethodId} onChange={(event) => setPaymentMethodId(event.target.value)}>
              <option value="">Seleccionar medio</option>
              {options?.payment_methods.map((method) => (
                <option key={method.id} value={method.id}>{method.name}</option>
              ))}
            </select>
          </label>
        </section>

        <section className="panel form">
          <h2>Agregar producto</h2>
          <label className="field">
            <span>Producto</span>
            <select value={productId} onChange={(event) => onProductChange(event.target.value)}>
              <option value="">Seleccionar producto</option>
              {products.map((product) => (
                <option key={product.id} value={product.id}>
                  {product.name} - stock {Number(product.available_stock).toLocaleString("es-UY")} {product.unit}
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
              <span>Precio</span>
              <input inputMode="decimal" type="number" min="0" step="0.01" value={unitPrice} onChange={(event) => setUnitPrice(event.target.value)} />
            </label>
          </div>
          <label className="field">
            <span>Descuento opcional</span>
            <input inputMode="decimal" type="number" min="0" step="0.01" value={discount} onChange={(event) => setDiscount(event.target.value)} />
          </label>
          <button className="button touch-button" type="button" onClick={addLine}>
            <Plus size={18} /> Agregar producto
          </button>
        </section>

        <section className="panel">
          <h2>Venta</h2>
          <div className="mobile-card-list">
            {lines.map((line, index) => (
              <article className="mobile-record-card" key={`${line.product_resource_id}-${index}`}>
                <div>
                  <strong>{line.product_name}</strong>
                  <span>{line.quantity} x {money(line.unit_price)}</span>
                </div>
                <div>
                  <strong>{money(numberValue(line.quantity) * numberValue(line.unit_price) - numberValue(line.discount))}</strong>
                  <button className="button secondary-button icon-button" type="button" onClick={() => setLines((current) => current.filter((_, itemIndex) => itemIndex !== index))}>
                    <Trash2 size={16} />
                  </button>
                </div>
              </article>
            ))}
            {lines.length === 0 ? <div className="empty-state">Todavia no agregaste productos.</div> : null}
          </div>
          <label className="field">
            <span>Observacion opcional</span>
            <input value={notes} onChange={(event) => setNotes(event.target.value)} />
          </label>
          <div className="sticky-mobile-total">
            <span>Total</span>
            <strong>{money(total)}</strong>
          </div>
          <button className="button touch-button" type="button" onClick={saveSale} disabled={saving}>
            <ShoppingCart size={18} /> {saving ? "Registrando..." : "Confirmar venta"}
          </button>
        </section>
      </div>
    </AppShell>
  );
}
