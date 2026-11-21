"""Admin controls for the notebook's GitHub Issues coordinator."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from api.dependencies import get_current_admin
from api.schemas import (
    AITaskAuthorization,
    AITaskControllerEnabled,
    AITaskControllerSettingsUpdate,
)
from services import ai_task_controller


router = APIRouter(
    prefix="/api/settings/ai-task-controller", tags=["ai-task-controller"]
)
logger = logging.getLogger("nivus.api.ai_task_controller")


def _raise_controller_error(error: ai_task_controller.TaskControllerError) -> None:
    raise HTTPException(
        status_code=error.http_status,
        detail={"code": error.code, "message": error.public_message},
    ) from error


@router.get("")
def read_controller(admin: str = Depends(get_current_admin)):
    return {"config": ai_task_controller.get_config(), "status": ai_task_controller.get_status()}


@router.get("/audit")
def read_audit(
    limit: int = Query(20, ge=1, le=100),
    admin: str = Depends(get_current_admin),
):
    return ai_task_controller.list_audit(limit)


@router.put("")
def save_controller_settings(
    payload: AITaskControllerSettingsUpdate,
    admin: str = Depends(get_current_admin),
):
    try:
        result = ai_task_controller.update_settings(payload, admin)
    except ai_task_controller.TaskControllerError as error:
        _raise_controller_error(error)
    except ai_task_controller.ai_providers.ProviderSecretError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    logger.info("Configuração do controlador GitHub atualizada pelo administrador %s.", admin)
    return result


@router.post("/connection-test")
def test_connection(admin: str = Depends(get_current_admin)):
    try:
        result = ai_task_controller.test_connection(admin)
    except ai_task_controller.TaskControllerError as error:
        _raise_controller_error(error)
    logger.info("Teste de conexão do controlador GitHub concluído pelo administrador %s.", admin)
    return result


@router.post("/refresh")
def refresh_queue(admin: str = Depends(get_current_admin)):
    try:
        return ai_task_controller.refresh_now()
    except ai_task_controller.TaskControllerError as error:
        _raise_controller_error(error)

@router.put("/enabled")
def set_enabled(
    payload: AITaskControllerEnabled,
    admin: str = Depends(get_current_admin),
):
    try:
        result = ai_task_controller.set_enabled(payload.enabled, admin)
    except ai_task_controller.TaskControllerError as error:
        _raise_controller_error(error)
    logger.info(
        "Controlador GitHub %s pelo administrador %s.",
        "habilitado" if payload.enabled else "desabilitado",
        admin,
    )
    return result


@router.post("/issues/{issue_number}/authorize")
def authorize_issue(
    issue_number: int,
    payload: AITaskAuthorization,
    admin: str = Depends(get_current_admin),
):
    try:
        return ai_task_controller.authorize_issue(
            issue_number, payload.confirm_free_tier_call, admin
        )
    except ai_task_controller.TaskControllerError as error:
        _raise_controller_error(error)

\n