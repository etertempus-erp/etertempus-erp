# Beta privada segura

Estado: preparada, no desplegada.

Esta guia deja Eter ERP listo para una beta privada con autenticacion, roles, CORS restringido, HTTPS mediante proxy y secretos fuera del repositorio.

## Decision de autenticacion

Eter ERP usa sesiones con cookie HTTP-only.

Motivo:

- La cookie no queda disponible para JavaScript.
- Reduce la exposicion de credenciales en el navegador.
- Funciona bien para una futura PWA.
- Permite invalidar sesiones desde la base de datos.

La cookie tiene:

- `HttpOnly`.
- `Secure` obligatorio en beta/produccion.
- `SameSite=lax` por defecto.
- expiracion configurable.

El token real no se guarda en base de datos. La base guarda solo un hash del token.

## Roles

Administrador:

- Accede a todos los modulos.
- Gestiona usuarios.
- Crea y edita recursos y formulas.
- Registra operaciones.
- Confirma operaciones.
- Anula operaciones.

Operador:

- Registra compras, ventas, produccion y gastos.
- Consulta stock, formulas, movimientos y dashboard.
- No gestiona usuarios.
- No anula operaciones.
- No modifica recursos ni formulas.

Consulta:

- Consulta dashboard, stock, formulas, movimientos e historiales.
- No crea, edita, confirma ni anula operaciones.

## Variables obligatorias

Backend:

```powershell
DATABASE_URL=
ENVIRONMENT=beta
AUTH_REQUIRED=true
AUTH_SECRET_KEY=
SESSION_COOKIE_NAME=eter_erp_session
SESSION_DURATION_MINUTES=480
COOKIE_SECURE=true
COOKIE_SAMESITE=lax
CORS_ALLOWED_ORIGINS=https://erp.tu-dominio.example
FRONTEND_PUBLIC_URL=https://erp.tu-dominio.example
```

Frontend:

```powershell
NEXT_PUBLIC_API_BASE_URL=https://erp.tu-dominio.example/api
NEXT_PUBLIC_FRONTEND_URL=https://erp.tu-dominio.example
NEXT_PUBLIC_ORGANIZATION_ID=00000000-0000-0000-0000-000000000001
```

Primer administrador:

```powershell
INITIAL_ADMIN_EMAIL=
INITIAL_ADMIN_PASSWORD=
INITIAL_ADMIN_NAME=Administrador
```

No guardar valores reales en Git.

## Desarrollo local

Iniciar PostgreSQL:

```powershell
docker compose up -d postgres
```

Backend:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
$env:DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/eter_erp"
python -m alembic upgrade head
uvicorn app.main:app --reload
```

Frontend:

```powershell
cd frontend
pnpm dev
```

Crear administrador local:

```powershell
cd backend
$env:INITIAL_ADMIN_EMAIL="tu-email@example.com"
$env:INITIAL_ADMIN_PASSWORD="una-clave-larga-y-segura"
$env:INITIAL_ADMIN_NAME="Dhioyi"
python scripts\create_initial_admin.py
```

Iniciar sesion:

1. Abrir `http://localhost:3000/login`.
2. Ingresar email y contrasena del administrador.

Ejecutar pruebas:

```powershell
cd backend
python -m pytest tests

cd ..\frontend
pnpm build
```

Detener servicios:

```powershell
docker compose down
```

## Beta

Antes de beta:

1. Copiar `.env.beta.example` a `.env.beta`.
2. Cambiar todos los secretos.
3. Definir el dominio real.
4. Apuntar DNS al servidor elegido.
5. Hacer backup.
6. Aplicar migraciones.
7. Crear administrador.
8. Probar login.
9. Probar compras, ventas, produccion, gastos y stock.

Backup:

```powershell
docker exec eter-erp-postgres pg_dump -U postgres -d eter_erp > backup-pre-beta.sql
```

Aplicar migraciones:

```powershell
cd backend
$env:DATABASE_URL="postgresql+psycopg://usuario:password@host:5432/eter_erp"
python -m alembic upgrade head
```

Crear administrador:

```powershell
cd backend
$env:INITIAL_ADMIN_EMAIL="admin@example.com"
$env:INITIAL_ADMIN_PASSWORD="clave-larga-y-segura"
$env:INITIAL_ADMIN_NAME="Administrador"
python scripts\create_initial_admin.py
```

## HTTPS y proxy

La beta queda preparada para Caddy.

Archivo:

```text
deploy/Caddyfile
```

Caddy obtiene certificados reales automaticamente cuando el dominio apunta al servidor y los puertos 80/443 estan disponibles.

No se incluyen certificados ni claves privadas en el repositorio.

## Recuperacion

Si el frontend no abre:

```powershell
docker compose -f compose.production.yml logs frontend
```

Si el backend no responde:

```powershell
docker compose -f compose.production.yml logs backend
```

Si PostgreSQL no inicia:

```powershell
docker compose -f compose.production.yml logs postgres
```

Ver estado de contenedores:

```powershell
docker compose -f compose.production.yml ps
```

Reiniciar servicios:

```powershell
docker compose -f compose.production.yml restart
```

Restaurar backup:

```powershell
docker exec -i eter-erp-postgres psql -U postgres -d eter_erp < backup-pre-beta.sql
```

## Deudas tecnicas conocidas

- CSRF dedicado queda pendiente para una beta mas amplia. Para beta privada se mitiga con cookie `SameSite=lax`, CORS restringido y HTTPS.
- La pantalla visual de gestion de usuarios todavia no existe; los endpoints ya estan preparados.
- No se implementa PWA en esta etapa.
- No se despliega todavia en internet.
