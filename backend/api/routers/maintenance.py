import logging

from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import get_current_admin
from api.schemas import MaintenanceUpdate
from services.maintenance import (
    MaintenanceStateError,
    read_maintenance_state,
    set_maintenance_mode,
)


logger = logging.getLogger("nivus.api.maintenance")
router = APIRouter(prefix="/api/maintenance", tags=["maintenance"])


@router.get("")
def get_maintenance_state(admin: str = Depends(get_current_admin)):
    try:
        return read_maintenance_state()
    except MaintenanceStateError as exc:
        logger.exception("Não foi possível ler o estado de manutenção.")
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("")
def update_maintenance_state(
    payload: MaintenanceUpdate,
    admin: str = Depends(get_current_admin),
):
    try:
        state = set_maintenance_mode(payload.enabled, admin)
    except MaintenanceStateError as exc:
        logger.exception("Não foi possível alterar o modo de manutenção.")
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    logger.info(
        "Modo de manutenção %s.",
        "ativado" if state["enabled"] else "desativado",
    )
    return state
