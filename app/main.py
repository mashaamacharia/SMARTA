from fastapi import FastAPI

from app.api.v1.router import router as v1_router
# BENCHMARK ONLY — not shipped to production
from app.api.v1.benchmark_sync.products_sync import router as benchmark_router
from app.core.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.include_router(v1_router)
app.include_router(benchmark_router)


@app.get("/health")
async def health():
    return {"status": "ok", "environment": settings.ENVIRONMENT}
