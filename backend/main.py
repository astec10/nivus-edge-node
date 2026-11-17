import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import (
    actuator,
    ai_providers,
    alerts,
    auth,
    maintenance,
    mobile_battery,
    nodes,
    settings,
    telemetry,
    users,
)
from database import init_db
from services.app_logging import configure_service_logger
from services.maintenance import record_boot_reset
from services.data_retention import cleanup_expired_records
from security import load_jwt_secret


# Fail fast when the JWT secret is missing, before the API starts accepting requests.
load_jwt_secret()
init_db()
record_boot_reset()
logger = configure_service_logger("api")
logger.info("Nivus API iniciada.")


async def _data_retention_loop():
    while True:
        try:
            removed = await asyncio.to_thread(cleanup_expired_records)
            if any(removed.values()):
                logger.info("Limpeza de retenção removeu registros: %s", removed)
        except Exception:
            logger.exception("Falha ao aplicar a política de retenção.")
        await asyncio.sleep(24 * 60 * 60)


@asynccontextmanager
async def lifespan(app):
    retention_task = asyncio.create_task(_data_retention_loop())
    try:
        yield
    finally:
        retention_task.cancel()
        try:
            await retention_task
        except asyncio.CancelledError:
            pass


CORS_ORIGINS = [
    item.strip()
    for item in os.environ.get(
        "NIVUS_CORS_ORIGINS",
        "",
    ).split(",")
    if item.strip()
]

app = FastAPI(title="Nivus Edge API", version="2.9.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok", "node": os.environ.get("NIVUS_NODE_NAME", "nivus-edge-node")}


app.include_router(auth.router)
app.include_router(telemetry.router)
app.include_router(actuator.router)
app.include_router(alerts.router)
app.include_router(settings.router)
app.include_router(ai_providers.router)
app.include_router(maintenance.router)
app.include_router(users.router)
app.include_router(mobile_battery.router)
app.include_router(nodes.router)
