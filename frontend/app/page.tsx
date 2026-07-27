"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  Beaker,
  Boxes,
  ClipboardList,
  PackageCheck,
  Plus,
  ReceiptText,
  ShoppingCart,
  WalletCards,
} from "lucide-react";

import { AppShell } from "@/components/AppShell";
import { apiGet, DashboardActivityItem, DashboardSummary, ORGANIZATION_ID } from "@/lib/api";
import { friendlyErrorMessage } from "@/lib/messages";

function formatMoney(value: string | number) {
  return Number(value || 0).toLocaleString("es-UY", {
    maximumFractionDigits: 2,
    style: "currency",
    currency: "UYU",
  });
}

function formatQuantity(value: string | number) {
  return Number(value || 0).toLocaleString("es-UY", {
    maximumFractionDigits: 2,
  });
}

function formatDate(value: string) {
  const [year, month, day] = value.split("-");
  if (!year || !month || !day) return value;
  return `${day}/${month}/${year}`;
}

function MetricSkeleton() {
  return <div className="metric-skeleton" aria-label="Cargando dato" />;
}

type PrimaryCardProps = {
  title: string;
  value: string;
  description: string;
  href: string;
  buttonLabel: string;
  icon: ReactNode;
  loading: boolean;
  alert?: boolean;
  extra?: React.ReactNode;
  secondaryHref?: string;
  secondaryLabel?: string;
};

function PrimaryCard({
  title,
  value,
  description,
  href,
  buttonLabel,
  icon,
  loading,
  alert,
  extra,
  secondaryHref,
  secondaryLabel,
}: PrimaryCardProps) {
  return (
    <article className={`panel dashboard-card primary-dashboard-card${alert ? " dashboard-alert-card" : ""}`}>
      <div className="dashboard-card-header">
        <span className="dashboard-icon">{icon}</span>
        <h3>{title}</h3>
      </div>
      {loading ? <MetricSkeleton /> : <div className="metric">{value}</div>}
      <p className="muted">{description}</p>
      {extra ? <div className="small-metric">{extra}</div> : null}
      <div className="dashboard-actions">
        <Link className="button" href={href}>
          {buttonLabel}
        </Link>
        {secondaryHref && secondaryLabel ? (
          <Link className="button secondary-button" href={secondaryHref}>
            {secondaryLabel}
          </Link>
        ) : null}
      </div>
    </article>
  );
}

type CompactCardProps = {
  title: string;
  value: string;
  description: string;
  href?: string;
  buttonLabel?: string;
  loading: boolean;
};

function CompactCard({ title, value, description, href, buttonLabel, loading }: CompactCardProps) {
  return (
    <article className="panel dashboard-card compact-dashboard-card">
      <h3>{title}</h3>
      {loading ? <MetricSkeleton /> : <div className="compact-metric">{value}</div>}
      <p className="muted">{description}</p>
      {href && buttonLabel ? (
        <Link className="button secondary-button" href={href}>
          {buttonLabel}
        </Link>
      ) : null}
    </article>
  );
}

export default function HomePage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [activity, setActivity] = useState<DashboardActivityItem[]>([]);
  const [summaryError, setSummaryError] = useState<string | null>(null);
  const [activityError, setActivityError] = useState<string | null>(null);
  const [loadingSummary, setLoadingSummary] = useState(true);
  const [loadingActivity, setLoadingActivity] = useState(true);

  const totalHistoricalSales = useMemo(
    () => Number(summary?.imported_sales_total ?? 0) + Number(summary?.system_sales_total ?? 0),
    [summary],
  );
  const totalHistoricalExpenses = useMemo(
    () => Number(summary?.imported_expenses_total ?? 0) + Number(summary?.system_expenses_total ?? 0),
    [summary],
  );

  async function loadSummary() {
    try {
      setLoadingSummary(true);
      setSummaryError(null);
      const data = await apiGet<DashboardSummary>(`/dashboard/summary?organization_id=${ORGANIZATION_ID}`);
      setSummary(data);
    } catch (err) {
      setSummary(null);
      setSummaryError(friendlyErrorMessage(err, "No se pudo actualizar el Centro de operaciones."));
    } finally {
      setLoadingSummary(false);
    }
  }

  async function loadActivity() {
    try {
      setLoadingActivity(true);
      setActivityError(null);
      const data = await apiGet<DashboardActivityItem[]>(`/dashboard/activity?organization_id=${ORGANIZATION_ID}`);
      setActivity(data);
    } catch (err) {
      setActivity([]);
      setActivityError(friendlyErrorMessage(err, "No se pudo cargar la actividad reciente."));
    } finally {
      setLoadingActivity(false);
    }
  }

  useEffect(() => {
    loadSummary();
    loadActivity();
  }, []);

  return (
    <AppShell>
      <section className="page-title dashboard-title">
        <div>
          <h1>Centro de operaciones</h1>
          <p>Resumen del estado actual de Eter Tempus.</p>
        </div>
        <Link className="button" href="/produccion">
          <Plus size={18} /> Nuevo lote
        </Link>
      </section>

      <div className="stack dashboard-stack">
        {summaryError ? <div className="notice notice-error">{summaryError}</div> : null}

        <section className="mobile-quick-actions" aria-labelledby="mobile-actions-title">
          <div className="section-heading">
            <h2 id="mobile-actions-title">Acciones rapidas</h2>
          </div>
          <div className="quick-action-grid">
            <Link className="quick-action" href="/compras/rapida">
              <ReceiptText size={20} />
              <span>Nueva compra</span>
            </Link>
            <Link className="quick-action" href="/gastos/rapido">
              <WalletCards size={20} />
              <span>Gasto rapido</span>
            </Link>
            <Link className="quick-action" href="/ventas/rapida">
              <ShoppingCart size={20} />
              <span>Nueva venta</span>
            </Link>
            <Link className="quick-action" href="/produccion/rapida">
              <ClipboardList size={20} />
              <span>Nuevo lote</span>
            </Link>
            <Link className="quick-action" href="/stock">
              <PackageCheck size={20} />
              <span>Ver stock</span>
            </Link>
            <Link className="quick-action" href="/stock?filter=low">
              <AlertTriangle size={20} />
              <span>Stock bajo</span>
            </Link>
          </div>
        </section>

        <section className="dashboard-section" aria-labelledby="business-status-title">
          <div className="section-heading">
            <h2 id="business-status-title">Estado del negocio</h2>
            <p>Indicadores principales para decidir rapido que atender primero.</p>
          </div>
          <div className="dashboard-primary-grid">
            <PrimaryCard
              title="Ventas"
              value={formatMoney(summary?.system_sales_total ?? 0)}
              description={`${summary?.system_sales_count ?? 0} ventas registradas en el ERP.`}
              href="/ventas"
              buttonLabel="Ver ventas"
              icon={<ShoppingCart size={20} />}
              loading={loadingSummary}
              extra={`${summary?.cancelled_system_sales_count ?? 0} ventas anuladas`}
            />

            <PrimaryCard
              title="Productos terminados"
              value={formatQuantity(summary?.finished_products_stock_total ?? 0)}
              description="Stock total actual de productos vendibles."
              href="/recursos"
              buttonLabel="Ver stock"
              icon={<PackageCheck size={20} />}
              loading={loadingSummary}
            />

            <PrimaryCard
              title="Stock bajo"
              value={String(summary?.low_stock_count ?? 0)}
              description="Recursos por debajo o igual al stock minimo."
              href="/recursos"
              buttonLabel="Ver recursos"
              icon={<AlertTriangle size={20} />}
              loading={loadingSummary}
              alert={Boolean(summary && summary.low_stock_count > 0)}
              extra={summary && summary.low_stock_count > 0 ? "Requiere revision" : "Sin alertas activas"}
            />

            <PrimaryCard
              title="Lotes registrados"
              value={String(summary?.production_batches_count ?? 0)}
              description="Lotes elaborados desde mezclas trazables."
              href="/produccion"
              buttonLabel="Nuevo lote"
              secondaryHref="/produccion"
              secondaryLabel="Ver produccion"
              icon={<ClipboardList size={20} />}
              loading={loadingSummary}
            />
          </div>
        </section>

        <section className="dashboard-section" aria-labelledby="management-title">
          <div className="section-heading">
            <h2 id="management-title">Gestion</h2>
            <p>Catalogos, compras y datos historicos separados de la operacion nueva.</p>
          </div>
          <div className="dashboard-compact-grid">
            <CompactCard
              title="Recursos"
              value={String(summary?.resources_count ?? 0)}
              description="Materias primas, packaging, productos y mezclas."
              href="/recursos"
              buttonLabel="Ver recursos"
              loading={loadingSummary}
            />
            <CompactCard
              title="Formulas"
              value={String(summary?.formulas_count ?? 0)}
              description="Recetas importadas y creadas en porcentaje."
              href="/formulas"
              buttonLabel="Ver formulas"
              loading={loadingSummary}
            />
            <CompactCard
              title="Compras"
              value={`${summary?.confirmed_purchases_count ?? 0} confirmadas`}
              description={`${summary?.draft_purchases_count ?? 0} borradores, ${summary?.cancelled_purchases_count ?? 0} anuladas. Total: ${formatMoney(summary?.confirmed_purchases_total ?? 0)}.`}
              href="/compras"
              buttonLabel="Ver compras"
              loading={loadingSummary}
            />
            <CompactCard
              title="Gastos"
              value={formatMoney(summary?.system_expenses_total ?? 0)}
              description={`${summary?.system_expenses_count ?? 0} gastos del ERP, ${summary?.cancelled_system_expenses_count ?? 0} anulados.`}
              href="/gastos"
              buttonLabel="Ver gastos"
              loading={loadingSummary}
            />
            <CompactCard
              title="Ventas importadas"
              value={formatMoney(summary?.imported_sales_total ?? 0)}
              description={`${summary?.imported_sales_count ?? 0} movimientos historicos. Total general: ${formatMoney(totalHistoricalSales)}.`}
              href="/ventas"
              buttonLabel="Ver ventas"
              loading={loadingSummary}
            />
            <CompactCard
              title="Gastos importados"
              value={formatMoney(summary?.imported_expenses_total ?? 0)}
              description={`${summary?.imported_expenses_count ?? 0} gastos historicos. Total general: ${formatMoney(totalHistoricalExpenses)}.`}
              href="/gastos?origin=imported"
              buttonLabel="Ver historicos"
              loading={loadingSummary}
            />
          </div>
        </section>

        <section className="dashboard-section" aria-labelledby="expenses-status-title">
          <div className="section-heading">
            <h2 id="expenses-status-title">Gastos</h2>
            <p>Seguimiento economico sin mezclarlo con compras de inventario.</p>
          </div>
          <div className="dashboard-compact-grid">
            <CompactCard
              title="Gastos del mes"
              value={formatMoney(summary?.month_expenses_total ?? 0)}
              description="Incluye gastos del ERP e historicos importados."
              href="/gastos"
              buttonLabel="Analizar"
              loading={loadingSummary}
            />
            <CompactCard
              title="Gastos del año"
              value={formatMoney(summary?.year_expenses_total ?? 0)}
              description={`${summary?.expenses_count ?? 0} gastos confirmados en el periodo.`}
              href="/gastos"
              buttonLabel="Ver listado"
              loading={loadingSummary}
            />
            <CompactCard
              title="Mayor categoria"
              value={summary?.top_expense_category_name ?? "-"}
              description={`Total: ${formatMoney(summary?.top_expense_category_total ?? 0)}.`}
              href="/gastos"
              buttonLabel="Filtrar"
              loading={loadingSummary}
            />
            <CompactCard
              title="Ventas del mismo periodo"
              value={formatMoney(summary?.sales_same_period_total ?? 0)}
              description="Comparacion simple. Todavia no calcula rentabilidad neta."
              href="/ventas"
              buttonLabel="Ver ventas"
              loading={loadingSummary}
            />
          </div>
        </section>

        <section className="dashboard-section" aria-labelledby="recent-activity-title">
          <div className="section-heading">
            <h2 id="recent-activity-title">Actividad reciente</h2>
            <p>Ultimos movimientos reales registrados en el ERP.</p>
          </div>
          <div className="panel activity-panel">
            {activityError ? <div className="notice notice-error">{activityError}</div> : null}
            {loadingActivity ? (
              <div className="activity-list" aria-label="Cargando actividad reciente">
                {[0, 1, 2].map((item) => (
                  <div className="activity-skeleton" key={item} />
                ))}
              </div>
            ) : null}
            {!loadingActivity && !activityError && activity.length === 0 ? (
              <div className="empty-state">
                Todavia no hay ventas, compras o lotes recientes para mostrar.
              </div>
            ) : null}
            {!loadingActivity && activity.length > 0 ? (
              <div className="activity-list">
                {activity.map((item) => {
                  const content = (
                    <>
                      <span className="activity-date">{formatDate(item.date)}</span>
                      <span className="activity-type">{item.type}</span>
                      <strong>{item.description}</strong>
                      <span className="activity-value">{item.value ?? "-"}</span>
                    </>
                  );
                  return item.href ? (
                    <Link className="activity-item" href={item.href} key={`${item.type}-${item.id}`}>
                      {content}
                    </Link>
                  ) : (
                    <div className="activity-item" key={`${item.type}-${item.id}`}>
                      {content}
                    </div>
                  );
                })}
              </div>
            ) : null}
          </div>
        </section>
      </div>
    </AppShell>
  );
}
