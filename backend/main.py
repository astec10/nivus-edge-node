import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import (
    actuator,
    alerts,
    auth,
    maintenance,
    mobile_battery,
    settings,
    telemetry,
    users,
)
from database import init_db
from services.app_logging import configure_service_logger
from services.maintenance import record_boot_reset
from security import load_jwt_secret


# Fail fast when the JWT secret is missing, before the API starts accepting requests.
load_jwt_secret()
init_db()
record_boot_reset()
logger = configure_service_logger("api")
logger.info("Nivus API iniciada.")

CORS_ORIGINS = [
    item.strip()
    for item in os.environ.get(
        "NIVUS_CORS_ORIGINS",
        "",
    ).split(",")
    if item.strip()
]

app = FastAPI(title="Nivus Edge API", version="2.8.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
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
app.include_router(maintenance.router)
app.include_router(users.router)
app.include_router(mobile_battery.router)
