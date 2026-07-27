# Backend

API inicial de Eter ERP con FastAPI.

## Ejecutar en desarrollo

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Migraciones con Alembic

Alembic controla los cambios de estructura de la base de datos desde `backend/alembic`.

### Base nueva

Para crear una base vacia desde cero:

```powershell
$env:DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/eter_erp"
alembic upgrade head
```

### Base existente con datos

Si la base ya fue creada con `database/schema.sql` y contiene datos reales, no ejecutes la migracion inicial encima. Primero verifica que la estructura ya coincida y luego marca la revision como aplicada:

```powershell
$env:DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/eter_erp"
alembic stamp head
```

Esto no crea ni borra tablas; solo registra que la base ya esta en la version actual.

### Crear una migracion futura

Despues de cambiar modelos SQLAlchemy:

```powershell
alembic revision --autogenerate -m "descripcion del cambio"
```

Revisar siempre el archivo generado antes de aplicarlo.

### Aplicar migraciones

```powershell
alembic upgrade head
```

### Revertir una migracion

```powershell
alembic downgrade -1
```

No usar `downgrade` sobre una base con datos reales sin respaldo y revision previa.

## Alcance actual

- Rutas base para recursos, formulas, produccion, compras, ventas, busqueda y dashboard.
- Entidades de dominio.
- Servicios puros para calculo de formulas y plan de produccion.
- Repositorios SQLAlchemy para PostgreSQL.
- Migracion inicial Alembic basada en el esquema actual.
- Pruebas de formulas, produccion, compras y ventas.

## Proximo paso tecnico

Mantener todos los cambios nuevos de estructura mediante Alembic.
