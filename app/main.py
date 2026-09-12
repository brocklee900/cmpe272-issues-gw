import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.errors import AppError, app_error_handler
from app.routers import events, health, issues, webhook
from app.schemas import ErrorResponse

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.http_client = httpx.AsyncClient(
        base_url=settings.github_api_base, timeout=settings.request_timeout_seconds
    )
    logger.info("Starting up, targeting repo %s", settings.repo_path)
    yield
    await app.state.http_client.aclose()


app = FastAPI(
    title="GitHub Issues Gateway",
    version="1.0.0",
    description="A small HTTP API that wraps GitHub Issues CRUD, comments, and webhooks.",
    lifespan=lifespan,
)

app.add_exception_handler(AppError, app_error_handler)


@app.middleware("http")
async def add_request_id_header(request: Request, call_next):
    response = await call_next(request)
    request_id = request.headers.get("x-request-id")
    if request_id:
        response.headers["X-Request-Id"] = request_id
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error")
    body = ErrorResponse(error="internal_error", message="An unexpected error occurred", status=500)
    return JSONResponse(status_code=500, content=body.model_dump(exclude_none=True))


app.include_router(health.router)
app.include_router(issues.router)
app.include_router(webhook.router)
app.include_router(events.router)
