"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Ban, Eye, Plus, RefreshCw, ShoppingCart, Trash2, Zap } from "lucide-react";

import { AppShell } from "@/components/AppShell";
import {
  apiGet,
  apiPost,
  ORGANIZATION_ID,
  ProductForSale,
  SaleOptions,
  SaleRead,
} from "@/lib/api";
import { friendlyErrorMessage } from "@/lib/messages";

type SaleLineDraft = {
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

function statusLabel(status: SaleRead["status"]) {
  const labels = {
    confirmed: "Confirmada",
    cancelled: "Anulada",
    draft: "Borrador",
    imported: "Historica",
  };
  return labels[status] ?? status;
}

export default function SalesPage() {
  const [options, setOptions] = useState<SaleOptions | null>(null);
  const [products, setProducts] = useState<ProductForSale[]>([]);
  const [sales, setSales] = useState<SaleRead[]>([]);
  const [selectedSale, setSelectedSale] = useState<SaleRead | null>(null);

  const [saleDate, setSaleDate] = useState(new Date().toISOString().slice(0, 10));
  const [channelId, setChannelId] = useState("");
  const [pointOfSaleId, setPointOfSaleId] = useState("");
  const [paymentMethodId, setPaymentMethodId] = useState("");
  const [customerName, setCustomerName] = useState("");
  const [notes, setNotes] = useState("");

  const [productId, setProductId] = useState("");
  const [quantity, setQuantity] = useState("1");
  const [unitPrice, setUnitPrice] = useState("");
  const [discount, setDiscount] = useState("0");
  const [lines, setLines] = useState<SaleLineDraft[]>([]);

  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [filterChannelId, setFilterChannelId] = useState("");
  const [filterPointId, setFilterPointId] = useState("");
  const [filterProductId, setFilterProductId] = useState("");
  const [filterPaymentId, setFilterPaymentId] = useState("");
  const [filterStatus, setFilterStatus] = useState("");

  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const selectedChannel = options?.channels.find((item) => item.id === channelId);
  const needsPointOfSale = selectedChannel
    ? selectedChannel.name.toLowerCase().includes("feria") || selectedChannel.name.toLowerCase().includes("punto")
    : false;

  const total = useMemo(
    () =>
      lines.reduce(
        (sum, line) => sum + Math.max(numberValue(line.quantity) * numberValue(line.unit_price) - numberValue(line.discount), 0),
        0,
      ),
    [lines],
  );

  async function loadData() {
    try {
      setError(null);
      const [optionData, productData] = await Promise.all([
        apiGet<SaleOptions>(`/sales/options?organization_id=${ORGANIZATION_ID}`),
        apiGet<ProductForSale[]>(`/sales/products/available-for-sale?organization_id=${ORGANIZATION_ID}`),
      ]);
      setOptions(optionData);
      setProducts(productData);
      if (!paymentMethodId && optionData.payment_methods.length > 0) {
        setPaymentMethodId(optionData.payment_methods[0].id);
      }
      await loadSales();
    } catch (err) {
      setError(friendlyErrorMessage(err, "No se pudieron cargar las ventas."));
    }
  }

  async function loadSales() {
    const params = new URLSearchParams({ organization_id: ORGANIZATION_ID });
    if (dateFrom) params.set("date_from", dateFrom);
    if (dateTo) params.set("date_to", dateTo);
    if (filterChannelId) params.set("channel_id", filterChannelId);
    if (filterPointId) params.set("point_of_sale_id", filterPointId);
    if (filterProductId) params.set("product_resource_id", filterProductId);
    if (filterPaymentId) params.set("payment_method_id", filterPaymentId);
    if (filterStatus) params.set("status", filterStatus);
    const data = await apiGet<SaleRead[]>(`/sales?${params.toString()}`);
    setSales(data);
  }

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function onProductChange(nextProductId: string) {
    setProductId(nextProductId);
    const product = products.find((item) => item.id === nextProductId);
    setUnitPrice(product?.suggested_price ?? "");
  }

  function addLine() {
    setMessage(null);
    setError(null);
    const product = products.find((item) => item.id === productId);
    if (!product) {
      setError("Selecciona un producto antes de agregarlo a la venta.");
      return;
    }
    if (numberValue(quantity) <= 0) {
      setError("La cantidad debe ser mayor a cero. No se permiten numeros negativos.");
      return;
    }
    if (numberValue(unitPrice) < 0 || numberValue(discount) < 0) {
      setError("El precio y el descuento no pueden ser negativos.");
      return;
    }
    if (numberValue(discount) > numberValue(quantity) * numberValue(unitPrice)) {
      setError("El descuento no puede ser mayor que el subtotal del producto.");
      return;
    }
    setLines((current) => [
      ...current,
      {
        product_resource_id: product.id,
        product_name: product.name,
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

  async function createSale() {
    setLoading(true);
    setMessage(null);
    setError(null);

    if (!channelId) {
      setError("Selecciona un canal de venta.");
      setLoading(false);
      return;
    }
    if (needsPointOfSale && !pointOfSaleId) {
      setError("Selecciona el punto de venta para este canal.");
      setLoading(false);
      return;
    }
    if (!paymentMethodId) {
      setError("Selecciona un medio de pago.");
      setLoading(false);
      return;
    }
    if (lines.length === 0) {
      setError("Debes agregar al menos un producto.");
      setLoading(false);
      return;
    }

    try {
      const response = await apiPost<{ sale: SaleRead }>("/sales", {
        organization_id: ORGANIZATION_ID,
        sale_date: saleDate,
        channel_id: channelId,
        point_of_sale_id: needsPointOfSale ? pointOfSaleId || null : null,
        customer_name: customerName || null,
        payment_method_id: paymentMethodId,
        notes: notes || null,
        lines: lines.map((line) => ({
          product_resource_id: line.product_resource_id,
          quantity: Number(line.quantity),
          unit_price: Number(line.unit_price),
          discount: Number(line.discount || 0),
        })),
      });
      setMessage(`La venta ${response.sale.code} se registro correctamente.`);
      setLines([]);
      setCustomerName("");
      setNotes("");
      setSelectedSale(response.sale);
      await Promise.all([loadSales(), refreshProducts()]);
    } catch (err) {
      setError(friendlyErrorMessage(err, "La venta no pudo registrarse y no se desconto stock."));
    } finally {
      setLoading(false);
    }
  }

  async function refreshProducts() {
    const productData = await apiGet<ProductForSale[]>(
      `/sales/products/available-for-sale?organization_id=${ORGANIZATION_ID}`,
    );
    setProducts(productData);
  }

  async function openSale(saleId: string) {
    try {
      setError(null);
      const data = await apiGet<SaleRead>(`/sales/${saleId}?organization_id=${ORGANIZATION_ID}`);
      setSelectedSale(data);
    } catch (err) {
      setError(friendlyErrorMessage(err, "No se pudo abrir el detalle de la venta."));
    }
  }

  async function cancelSale(sale: SaleRead) {
    const reason = window.prompt(`Motivo para anular ${sale.code}`);
    if (!reason) return;
    try {
      setError(null);
      const data = await apiPost<SaleRead>(`/sales/${sale.id}/cancel`, {
        organization_id: ORGANIZATION_ID,
        reason,
      });
      setMessage(`La venta ${data.code} fue anulada y el stock fue devuelto.`);
      setSelectedSale(data);
      await Promise.all([loadSales(), refreshProducts()]);
    } catch (err) {
      setError(friendlyErrorMessage(err, "No se pudo anular la venta."));
    }
  }

  return (
    <AppShell>
      <section className="page-title">
        <div>
          <h1>Ventas</h1>
          <p>Carga rapida, historial y descuento automatico de stock.</p>
        </div>
        <div className="row-actions">
          <Link className="button" href="/ventas/rapida">
            <Zap size={18} /> Venta rapida
          </Link>
          <button className="button secondary-button" type="button" onClick={() => loadData()}>
            <RefreshCw size={18} /> Actualizar
          </button>
        </div>
      </section>

      <div className="stack">
        {message ? <div className="notice notice-ok">{message}</div> : null}
        {error ? <div className="notice notice-error">{error}</div> : null}

        <section className="panel">
          <h2>Nueva venta</h2>
          <div className="form wide-form">
            <div className="form-grid">
              <div className="field">
                <label htmlFor="sale-date">Fecha</label>
                <input id="sale-date" type="date" value={saleDate} onChange={(event) => setSaleDate(event.target.value)} />
              </div>
              <div className="field">
                <label htmlFor="channel">Canal</label>
                <select id="channel" value={channelId} onChange={(event) => setChannelId(event.target.value)}>
                  <option value="">Seleccionar canal</option>
                  {options?.channels.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label htmlFor="point">Punto de venta</label>
                <select
                  id="point"
                  value={pointOfSaleId}
                  onChange={(event) => setPointOfSaleId(event.target.value)}
                  disabled={!needsPointOfSale}
                >
                  <option value="">{needsPointOfSale ? "Seleccionar punto" : "No corresponde"}</option>
                  {options?.points_of_sale.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label htmlFor="payment">Medio de pago</label>
                <select id="payment" value={paymentMethodId} onChange={(event) => setPaymentMethodId(event.target.value)}>
                  <option value="">Seleccionar medio</option>
                  {options?.payment_methods.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label htmlFor="customer">Cliente opcional</label>
                <input id="customer" value={customerName} onChange={(event) => setCustomerName(event.target.value)} />
              </div>
              <div className="field">
                <label htmlFor="notes">Observaciones</label>
                <input id="notes" value={notes} onChange={(event) => setNotes(event.target.value)} />
              </div>
            </div>

            <div className="line-builder">
              <div className="field">
                <label htmlFor="product">Producto</label>
                <select id="product" value={productId} onChange={(event) => onProductChange(event.target.value)}>
                  <option value="">Seleccionar producto</option>
                  {products.map((product) => (
                    <option key={product.id} value={product.id}>
                      {product.name} - stock {Number(product.available_stock).toLocaleString("es-UY")} {product.unit}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label htmlFor="quantity">Cantidad</label>
                <input id="quantity" type="number" min="0.001" step="0.001" value={quantity} onChange={(event) => setQuantity(event.target.value)} />
              </div>
              <div className="field">
                <label htmlFor="unit-price">Precio unitario</label>
                <input id="unit-price" type="number" min="0" step="0.01" value={unitPrice} onChange={(event) => setUnitPrice(event.target.value)} />
              </div>
              <div className="field">
                <label htmlFor="discount">Descuento</label>
                <input id="discount" type="number" min="0" step="0.01" value={discount} onChange={(event) => setDiscount(event.target.value)} />
              </div>
              <button className="button" type="button" onClick={addLine}>
                <Plus size={18} /> Agregar
              </button>
            </div>

            <div className="table-scroll">
            <table className="table">
              <thead>
                <tr>
                  <th>Producto</th>
                  <th>Cantidad</th>
                  <th>Precio</th>
                  <th>Descuento</th>
                  <th>Total</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {lines.map((line, index) => (
                  <tr key={`${line.product_resource_id}-${index}`}>
                    <td>{line.product_name}</td>
                    <td>{line.quantity}</td>
                    <td>{money(line.unit_price)}</td>
                    <td>{money(line.discount)}</td>
                    <td>{money(numberValue(line.quantity) * numberValue(line.unit_price) - numberValue(line.discount))}</td>
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
                    <td className="muted" colSpan={6}>
                      Agrega productos para confirmar la venta.
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

            <button className="button" type="button" onClick={createSale} disabled={loading}>
              <ShoppingCart size={18} /> {loading ? "Registrando..." : "Confirmar venta"}
            </button>
          </div>
        </section>

        <section className="panel">
          <h2>Historial</h2>
          <div className="filters-grid">
            <div className="field">
              <label>Desde</label>
              <input type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} />
            </div>
            <div className="field">
              <label>Hasta</label>
              <input type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} />
            </div>
            <div className="field">
              <label>Canal</label>
              <select value={filterChannelId} onChange={(event) => setFilterChannelId(event.target.value)}>
                <option value="">Todos</option>
                {options?.channels.map((item) => (
                  <option key={item.id} value={item.id}>{item.name}</option>
                ))}
              </select>
            </div>
            <div className="field">
              <label>Punto</label>
              <select value={filterPointId} onChange={(event) => setFilterPointId(event.target.value)}>
                <option value="">Todos</option>
                {options?.points_of_sale.map((item) => (
                  <option key={item.id} value={item.id}>{item.name}</option>
                ))}
              </select>
            </div>
            <div className="field">
              <label>Producto</label>
              <select value={filterProductId} onChange={(event) => setFilterProductId(event.target.value)}>
                <option value="">Todos</option>
                {products.map((item) => (
                  <option key={item.id} value={item.id}>{item.name}</option>
                ))}
              </select>
            </div>
            <div className="field">
              <label>Pago</label>
              <select value={filterPaymentId} onChange={(event) => setFilterPaymentId(event.target.value)}>
                <option value="">Todos</option>
                {options?.payment_methods.map((item) => (
                  <option key={item.id} value={item.id}>{item.name}</option>
                ))}
              </select>
            </div>
            <div className="field">
              <label>Estado</label>
              <select value={filterStatus} onChange={(event) => setFilterStatus(event.target.value)}>
                <option value="">Todos</option>
                <option value="confirmed">Confirmada</option>
                <option value="cancelled">Anulada</option>
                <option value="imported">Historica</option>
              </select>
            </div>
            <button className="button secondary-button" type="button" onClick={() => loadSales()}>
              Filtrar
            </button>
          </div>

          <div className="table-scroll">
          <table className="table">
            <thead>
              <tr>
                <th>Fecha</th>
                <th>Codigo</th>
                <th>Canal</th>
                <th>Punto</th>
                <th>Productos</th>
                <th>Total</th>
                <th>Pago</th>
                <th>Estado</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {sales.map((sale) => (
                <tr key={sale.id}>
                  <td>{sale.sale_date}</td>
                  <td>{sale.code}</td>
                  <td>{sale.channel_name ?? "-"}</td>
                  <td>{sale.point_of_sale_name ?? "-"}</td>
                  <td>{sale.products_summary}</td>
                  <td>{money(sale.total)}</td>
                  <td>{sale.payment_method_name ?? "-"}</td>
                  <td>{statusLabel(sale.status)}</td>
                  <td>
                    <div className="row-actions">
                      <button className="button secondary-button icon-button" type="button" onClick={() => openSale(sale.id)} aria-label="Ver detalle">
                        <Eye size={16} />
                      </button>
                      {sale.source === "system" && sale.status === "confirmed" ? (
                        <button className="button secondary-button icon-button" type="button" onClick={() => cancelSale(sale)} aria-label="Anular">
                          <Ban size={16} />
                        </button>
                      ) : null}
                    </div>
                  </td>
                </tr>
              ))}
              {sales.length === 0 ? (
                <tr>
                  <td className="muted" colSpan={9}>
                    No hay ventas para esos filtros.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
          </div>
        </section>

        {selectedSale ? (
          <section className="panel">
            <h2>Detalle {selectedSale.code}</h2>
            <p className="muted">
              {selectedSale.source === "imported"
                ? "Venta historica importada. No descuenta stock."
                : "Venta registrada desde el ERP con movimientos de inventario."}
            </p>
            <div className="table-scroll">
            <table className="table">
              <thead>
                <tr>
                  <th>Producto</th>
                  <th>Cantidad</th>
                  <th>Precio</th>
                  <th>Descuento</th>
                  <th>Total</th>
                </tr>
              </thead>
              <tbody>
                {selectedSale.lines.map((line) => (
                  <tr key={line.id}>
                    <td>{line.product_name}</td>
                    <td>{line.quantity}</td>
                    <td>{money(line.unit_price)}</td>
                    <td>{money(line.discount)}</td>
                    <td>{money(line.line_total)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            </div>
            {selectedSale.movements.length > 0 ? (
              <>
                <h2>Movimientos</h2>
                <div className="table-scroll">
                <table className="table">
                  <tbody>
                    {selectedSale.movements.map((movement) => (
                      <tr key={movement.id}>
                        <td>{movement.resource_name}</td>
                        <td>{movement.type}</td>
                        <td>{movement.quantity}</td>
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
