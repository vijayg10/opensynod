from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, health
from app.api.org import router as org_router
from app.api.panels import router as panels_router
from app.api.sessions import router as sessions_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.tracing import configure_tracing


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    configure_logging()
    configure_tracing(service_name="opensynod-api")
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="AI Round Table Conference",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.environment != "production" else None,
        redoc_url=None,
    )

    # ── CORS ───────────────────────────────────────────────────────────────
    allowed_origins = [
        "http://localhost:5173",
        "http://localhost:3000",
    ]
    if settings.environment == "production":
        # In production, CORS origins come from settings or env
        pass

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-CSRF-Token"],
        expose_headers=["X-Request-ID"],
    )

    # ── Security headers middleware ─────────────────────────────────────────
    @app.middleware("http")
    async def security_headers(request: Request, call_next: object) -> Response:
        response: Response = await call_next(request)  # type: ignore[operator]
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "0"  # CSP is the modern replacement
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        # Only set HSTS on HTTPS environments
        if settings.environment == "production":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "connect-src 'self' wss: https:; "
                "font-src 'self'; "
                "frame-ancestors 'none';"
            )
        return response

    # ── Prometheus metrics ─────────────────────────────────────────────────
    # NOTE: prometheus_fastapi_instrumentator is incompatible with current FastAPI
    # version (_IncludedRouter has no .path attribute). Disabled until pinned to
    # a compatible release.
    # try:
    #     from prometheus_fastapi_instrumentator import Instrumentator
    #     Instrumentator(...).instrument(app).expose(app, ...)
    # except ImportError:
    #     pass

    # ── Routers ────────────────────────────────────────────────────────────
    app.include_router(health.router)
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(panels_router, prefix="/api/v1")
    app.include_router(sessions_router, prefix="/api/v1")
    app.include_router(org_router, prefix="/api/v1")

    return app


app = create_app()
