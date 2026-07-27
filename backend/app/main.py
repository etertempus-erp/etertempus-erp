from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import dashboard, expenses, formulas, movements, production, purchases, resources, sales, search

app = FastAPI(
    title="Eter ERP API",
    version="0.1.0",
    description="API inicial para recursos, formulas, produccion y ventas.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:3000", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(resources.router, prefix="/resources", tags=["resources"])
app.include_router(formulas.router, prefix="/formulas", tags=["formulas"])
app.include_router(production.router, prefix="/production", tags=["production"])
app.include_router(purchases.router, prefix="/purchases", tags=["purchases"])
app.include_router(sales.router, prefix="/sales", tags=["sales"])
app.include_router(expenses.router, prefix="/expenses", tags=["expenses"])
app.include_router(movements.router, prefix="/movements", tags=["movements"])
app.include_router(search.router, prefix="/search", tags=["search"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
