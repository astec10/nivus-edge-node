import logging
import re
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from api.dependencies import get_current_admin
from api.schemas import AIExecutorParallelRequest, AIExecutorRequest
from services import ai_executor


router = APIRouter(prefix="/api/ai/executor", tags=["ai-executor"])
logger = logging.getLogger("nivus.api.ai_executor")
PROVIDER_ID_PATTERN = re.compile(r"^[a-f0-9]{32}$")


@router.post("/parallel")
def complete_parallel(
    payload: AIExecutorParallelRequest, admin: str = Depends(get_current_admin)
):
    try:
        result = ai_executor.execute_parallel(payload, admin)
    except ai_executor.InferenceRequestError as error:
        logger.info("Parallel executor rejected a request: %s.", error.code)
        raise HTTPException(
            status_code=error.http_status,
            detail={"code": error.code, "message": error.public_message},
        ) from error
    logger.info(
        "Parallel executor finished: %d succeeded, %d failed.",
        result["success_count"], result["failure_count"],
    )
    return result


@router.post("/complete")
def complete(payload: AIExecutorRequest, admin: str = Depends(get_current_admin)):
    if not PROVIDER_ID_PATTERN.fullmatch(payload.provider_id):
        raise HTTPException(status_code=404, detail="Provedor não encontrado.")
    try:
        result = ai_executor.execute(payload, admin)
    except ai_executor.InferenceRequestError as error:
        logger.info("Executor rejected a request: %s.", error.code)
        raise HTTPException(
            status_code=error.http_status,
            detail={"code": error.code, "message": error.public_message},
        ) from error
    logger.info("Executor request completed.")
    return result


@router.post("/requests/{request_id}/cancel")
def cancel_request(request_id: UUID, admin: str = Depends(get_current_admin)):
    cancelled = ai_executor.cancel_request(str(request_id), admin)
    if not cancelled:
        raise HTTPException(
            status_code=409,
            detail="A solicitação não está ativa ou não pertence a este administrador.",
        )
    return {
        "request_id": str(request_id),
        "status": "cancel_requested",
        "note": "Se a chamada já foi enviada, o provedor ainda pode concluir e cobrar a solicitação.",
    }


@router.get("/audit")
def get_executor_audit(
    limit: int = Query(50, ge=1, le=200),
    admin: str = Depends(get_current_admin),
):
    return ai_executor.list_audit(limit)
