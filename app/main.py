import logging
import time

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api import analytics, categories, parameters, passports, products, templates
from app.core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("app.middleware")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Система генерации паспортов изделий по шаблонам DOCX (FastAPI + PostgreSQL)",
    version="1.0.0",
)


# Starlette Middleware: замер времени обработки запроса и логирование
@app.middleware("http")
async def process_time_and_logging_middleware(request: Request, call_next):
    start_time = time.perf_counter()

    response = await call_next(request)

    process_time_ms = (time.perf_counter() - start_time) * 1000
    response.headers["X-Process-Time"] = f"{process_time_ms:.2f}ms"

    logger.info(
        f"{request.method} {request.url.path} -> Status: {response.status_code} "
        f"[Time: {process_time_ms:.2f}ms]"
    )
    return response


# Подключение роутеров API
app.include_router(categories.router, prefix="/api/v1")
app.include_router(parameters.router, prefix="/api/v1")
app.include_router(products.router, prefix="/api/v1")
app.include_router(templates.router, prefix="/api/v1")
app.include_router(passports.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")


@app.get("/", include_in_schema=False)
async def root():
    return JSONResponse(
        content={
            "service": settings.PROJECT_NAME,
            "status": "online",
            "docs_url": "/docs",
        }
    )
