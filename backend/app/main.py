from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import require_roles
from app.api.routes import auth, dashboard, expenses, formulas, movements, production, purchases, resources, sales, search, users
from app.core.config import settings
from app.db.models import UserRole

app = FastAPI(
    title="Eter ERP API",
    version="0.1.0",
    description="API inicial para recursos, formulas, produccion y ventas.",
    docs_url=None if settings.environment in {"beta", "production"} else "/docs",
    redoc_url=None if settings.environment in {"beta", "production"} else "/redoc",
    openapi_url=None if settings.environment in {"beta", "production"} else "/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "same-origin")
    return response


read_access = [Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR, UserRole.VIEWER))]

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(resources.router, prefix="/resources", tags=["resources"], dependencies=read_access)
app.include_router(formulas.router, prefix="/formulas", tags=["formulas"], dependencies=read_access)
app.include_router(production.router, prefix="/production", tags=["production"], dependencies=read_access)
app.include_router(purchases.router, prefix="/purchases", tags=["purchases"], dependencies=read_access)
app.include_router(sales.router, prefix="/sales", tags=["sales"], dependencies=read_access)
app.include_router(expenses.router, prefix="/expenses", tags=["expenses"], dependencies=read_access)
app.include_router(movements.router, prefix="/movements", tags=["movements"], dependencies=read_access)
app.include_router(search.router, prefix="/search", tags=["search"], dependencies=read_access)
app.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"], dependencies=read_access)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
