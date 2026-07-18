"""
Knpodly FastAPI application entrypoint.

Wires together: CORS, all v1 routers, startup catalogue sync, and OpenAPI
metadata (auto-generated docs are available at /docs and /redoc).
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.routers import admin, auth, console, health, images, users, vms, ws
from app.core.arq_pool import close_arq_pool, init_arq_pool
from app.core.config import get_settings
from app.db.session import AsyncSessionLocal
from app.services import image_discovery
from app.services.redis_bus import close_redis_bus, init_redis_bus

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # One-shot catalogue sync on boot so the OS list is populated immediately;
    # the scheduler container's watchdog handles ongoing changes at runtime.
    async with AsyncSessionLocal() as db:
        await image_discovery.sync_to_database(db)

    await init_arq_pool()
    await init_redis_bus()
    try:
        yield
    finally:
        await close_redis_bus()
        await close_arq_pool()


app = FastAPI(
    title="Knpodly API",
    description="Self-hosted educational Linux lab platform — REST API",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.app_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_PREFIX = "/api/v1"
app.include_router(health.router, prefix=API_PREFIX)
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(users.router, prefix=API_PREFIX)
app.include_router(images.router, prefix=API_PREFIX)
app.include_router(vms.router, prefix=API_PREFIX)
app.include_router(admin.router, prefix=API_PREFIX)
app.include_router(ws.router)  # WebSocket routes are not under /api/v1 (see nginx.conf /ws/ location)
app.include_router(console.router)  # /console/{token} — see nginx.conf /console/ location
