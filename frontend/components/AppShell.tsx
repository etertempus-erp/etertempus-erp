"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Beaker, Boxes, ClipboardList, Home, Menu, PackageCheck, ReceiptText, Search, ShoppingCart, WalletCards } from "lucide-react";

import { apiGet, ORGANIZATION_ID, SearchResult } from "@/lib/api";
import { friendlyErrorMessage } from "@/lib/messages";

export function AppShell({ children }: { children: React.ReactNode }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [mobileMoreOpen, setMobileMoreOpen] = useState(false);

  useEffect(() => {
    const trimmed = query.trim();
    if (trimmed.length < 2) {
      setResults([]);
      setError(null);
      return;
    }

    const timeout = window.setTimeout(async () => {
      try {
        setError(null);
        const data = await apiGet<SearchResult[]>(
          `/search?organization_id=${ORGANIZATION_ID}&q=${encodeURIComponent(trimmed)}`,
        );
        setResults(data);
      } catch (err) {
        setResults([]);
        setError(friendlyErrorMessage(err, "No se pudo buscar en el ERP."));
      }
    }, 250);

    return () => window.clearTimeout(timeout);
  }, [query]);

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">Eter ERP</div>
        <div className="global-search">
          <label className="global-search-box">
            <Search size={17} />
            <input
              value={query}
              placeholder="Buscar..."
              onChange={(event) => setQuery(event.target.value)}
            />
          </label>
          {query.trim().length >= 2 ? (
            <div className="global-search-results">
              {error ? <div className="global-search-empty">{error}</div> : null}
              {!error && results.length === 0 ? (
                <div className="global-search-empty">Sin resultados.</div>
              ) : null}
              {results.map((result) => (
                <Link
                  href={result.href}
                  key={`${result.type}-${result.id}`}
                  className="global-search-result"
                  onClick={() => {
                    setQuery("");
                    setResults([]);
                  }}
                >
                  <span>{result.type}</span>
                  <strong>{result.title}</strong>
                  <small>{result.subtitle}</small>
                </Link>
              ))}
            </div>
          ) : null}
        </div>
        <nav className="nav" aria-label="Principal">
          <Link href="/">
            <Home size={18} /> Inicio
          </Link>
          <Link href="/recursos">
            <Boxes size={18} /> Recursos
          </Link>
          <Link href="/formulas">
            <Beaker size={18} /> Formulas
          </Link>
          <Link href="/produccion">
            <ClipboardList size={18} /> Produccion
          </Link>
          <Link href="/compras">
            <ReceiptText size={18} /> Compras
          </Link>
          <Link href="/ventas">
            <ShoppingCart size={18} /> Ventas
          </Link>
          <Link href="/gastos">
            <WalletCards size={18} /> Gastos
          </Link>
        </nav>
        <nav className="mobile-nav" aria-label="Principal movil">
          <Link href="/" onClick={() => setMobileMoreOpen(false)}>
            <Home size={18} /> Inicio
          </Link>
          <Link href="/stock" onClick={() => setMobileMoreOpen(false)}>
            <PackageCheck size={18} /> Stock
          </Link>
          <Link href="/compras/rapida" onClick={() => setMobileMoreOpen(false)}>
            <ReceiptText size={18} /> Comprar
          </Link>
          <Link href="/ventas/rapida" onClick={() => setMobileMoreOpen(false)}>
            <ShoppingCart size={18} /> Vender
          </Link>
          <button type="button" onClick={() => setMobileMoreOpen((current) => !current)}>
            <Menu size={18} /> Mas
          </button>
        </nav>
        {mobileMoreOpen ? (
          <div className="mobile-more-menu">
            <Link href="/gastos" onClick={() => setMobileMoreOpen(false)}>Gastos</Link>
            <Link href="/produccion/rapida" onClick={() => setMobileMoreOpen(false)}>Produccion</Link>
            <Link href="/recursos" onClick={() => setMobileMoreOpen(false)}>Recursos</Link>
            <Link href="/formulas" onClick={() => setMobileMoreOpen(false)}>Formulas</Link>
            <Link href="/movimientos" onClick={() => setMobileMoreOpen(false)}>Movimientos</Link>
            <span>Proveedores</span>
            <span>Configuracion</span>
          </div>
        ) : null}
      </aside>
      <main className="main">{children}</main>
    </div>
  );
}
