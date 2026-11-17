import logging
import re

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.dependencies import get_current_admin
from api.schemas import (
    AIProviderCreate,
    AIProviderCredentialUpdate,
    AIProviderEnabled,
    AIProviderUpdate,
)
from services import ai_providers


router = APIRouter(prefix="/api/settings/ai-providers", tags=["ai-providers"])
logger = logging.getLogger("nivus.api.ai_providers")
PROVIDER_ID_PATTERN = re.compile(r"^[a-f0-9]{32}$")


def _validate_provider_id(provider_id: str) -> None:
    if not PROVIDER_ID_PATTERN.fullmatch(provider_id):
        raise HTTPException(status_code=404, detail="Provedor não encontrado.")


def _raise_provider_error(error: Exception) -> None:
    if isinstance(error, ai_providers.ProviderSecretError):
        raise HTTPException(status_code=503, detail=str(error)) from error
    if isinstance(error, KeyError):
        raise HTTPException(status_code=404, detail="Provedor não encontrado.") from error
    if isinstance(error, (ValueError, ConnectionError)):
        raise HTTPException(status_code=422, detail=str(error)) from error
    raise HTTPException(status_code=500, detail="Não foi possível atualizar o provedor.") from error


@router.get("/catalog")
def get_catalog(admin: str = Depends(get_current_admin)):
    return ai_providers.provider_catalog()


@router.get("")
def get_connections(admin: str = Depends(get_current_admin)):
    return ai_providers.list_connections(admin)


@router.get("/audit")
def get_provider_audit(
    limit: int = Query(50, ge=1, le=100),
    admin: str = Depends(get_current_admin),
):
    return ai_providers.list_audit(limit)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_connection(payload: AIProviderCreate, admin: str = Depends(get_current_admin)):
    try:
        result = ai_providers.create_connection(payload, admin)
    except (ai_providers.ProviderSecretError, ValueError) as error:
        _raise_provider_error(error)
    logger.info("Configuração de provedor criada por administrador %s.", admin)
    return result


@router.patch("/{provider_id}")
def update_connection(
    provider_id: str, payload: AIProviderUpdate, admin: str = Depends(get_current_admin)
):
    _validate_provider_id(provider_id)
    try:
        result = ai_providers.update_connection(provider_id, payload, admin)
    except (ai_providers.ProviderSecretError, KeyError, ValueError) as error:
        _raise_provider_error(error)
    logger.info("Configuração de provedor atualizada por administrador %s.", admin)
    return result


@router.put("/{provider_id}/credential")
def replace_credential(
    provider_id: str,
    payload: AIProviderCredentialUpdate,
    admin: str = Depends(get_current_admin),
):
    _validate_provider_id(provider_id)
    try:
        result = ai_providers.replace_credential(
            provider_id, payload.api_key.get_secret_value(), admin
        )
    except (ai_providers.ProviderSecretError, KeyError, ValueError) as error:
        _raise_provider_error(error)
    logger.info("Credencial de provedor substituída por administrador %s.", admin)
    return result


@router.post("/{provider_id}/test")
def test_connection(provider_id: str, admin: str = Depends(get_current_admin)):
    _validate_provider_id(provider_id)
    try:
        result = ai_providers.test_connection(provider_id, admin)
    except (ai_providers.ProviderSecretError, KeyError, ValueError, ConnectionError) as error:
        _raise_provider_error(error)
    logger.info("Teste explícito do provedor concluído por administrador %s: %s.",
                admin, result.get("status", "unknown"))
    return result


@router.post("/{provider_id}/enabled")
def set_connection_enabled(
    provider_id: str, payload: AIProviderEnabled, admin: str = Depends(get_current_admin)
):
    _validate_provider_id(provider_id)
    try:
        return ai_providers.set_enabled(provider_id, payload.enabled, admin)
    except (ai_providers.ProviderSecretError, KeyError, ValueError) as error:
        _raise_provider_error(error)


@router.delete("/{provider_id}")
def delete_connection(provider_id: str, admin: str = Depends(get_current_admin)):
    _validate_provider_id(provider_id)
    if not ai_providers.delete_connection(provider_id, admin):
        raise HTTPException(status_code=404, detail="Provedor não encontrado.")
    logger.warning("Configuração de provedor removida por administrador %s.", admin)
    return {"status": "deleted", "provider_id": provider_id}
