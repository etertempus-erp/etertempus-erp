# Eter ERP

ERP modular para la gestion operativa de Eter Tempus, con foco inicial en blends, tisanas, produccion artesanal, inventario trazable y ventas por canal.

## Objetivo de la version 0.1

Permitir el ciclo operativo minimo:

1. Registrar recursos: materias primas, packaging y productos.
2. Crear formulas versionadas en porcentaje.
3. Elaborar un lote usando una formula.
4. Registrar movimientos de inventario.
5. Dejar la mezcla disponible para envasado y venta en futuras iteraciones.

## Estructura

```text
eter-erp/
  docs/          Documentacion funcional y decisiones
  database/      ERD y esquema PostgreSQL inicial
  backend/       API FastAPI y casos de uso
  frontend/      Interfaz Next.js inicial
```

## Estado

Eter ERP ya cuenta con modulos operativos para recursos, formulas, compras, ventas, gastos, produccion, stock, movimientos y centro de operaciones.

La preparacion de beta privada agrega:

- autenticacion con cookie HTTP-only;
- roles `admin`, `operator` y `viewer`;
- CORS configurable por entorno;
- migraciones Alembic;
- Dockerfiles para backend y frontend;
- compose de produccion separado;
- guia de beta segura.

Ver [docs/08_beta_privada_segura.md](docs/08_beta_privada_segura.md).
