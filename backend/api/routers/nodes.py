from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator

from api.dependencies import get_current_admin
from services.nodes import (
    EnrollmentAuthenticationError,
    HeartbeatReplayError,
    NodeAuthenticationError,
    create_node_enrollment,
    create_node_session,
    enroll_node,
    list_nodes,
    process_node_heartbeat,
    revoke_node,
)


router = APIRouter(prefix="/api/nodes", tags=["nodes"])

NodeCapability = Literal[
    "telemetry.cpu",
    "telemetry.memory",
    "telemetry.disk",
    "telemetry.host_battery",
    "telemetry.temperature",
    "telemetry.power_estimate",
]


class NodeEnrollment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=48, pattern=r"^[A-Za-z0-9][A-Za-z0-9 _.-]{0,47}$")

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        clean = " ".join(value.split())
        if not clean:
            raise ValueError("Informe o nome do nó.")
        return clean


class NodeHeartbeat(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_id: str = Field(min_length=40, max_length=128, pattern=r"^[A-Za-z0-9_-]+$")
    sequence: StrictInt = Field(ge=0, le=2**63 - 1)
    agent_version: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,63}$")
    schema_version: StrictInt = Field(ge=1, le=100)
    capabilities: list[NodeCapability] = Field(default_factory=list, max_length=16)

    @field_validator("capabilities")
    @classmethod
    def capabilities_are_unique(cls, value: list[NodeCapability]) -> list[NodeCapability]:
        if len(set(value)) != len(value):
            raise ValueError("A lista de capacidades contém duplicatas.")
        return value


@router.post("/enrollments", status_code=201)
def create_enrollment(admin: str = Depends(get_current_admin)):
    return create_node_enrollment()


@router.post("/enroll", status_code=201)
def enroll(
    payload: NodeEnrollment,
    enrollment_code: str = Header(
        ..., alias="X-Nivus-Enrollment-Code", min_length=40, max_length=128
    ),
):
    try:
        return enroll_node(enrollment_code, payload.name)
    except EnrollmentAuthenticationError:
        raise HTTPException(
            status_code=401,
            detail="Código de pareamento inválido, expirado ou já utilizado.",
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


@router.post("/session")
def renew_session(
    node_token: str = Header(..., alias="X-Nivus-Node-Token", min_length=40, max_length=128),
):
    try:
        return create_node_session(node_token)
    except NodeAuthenticationError:
        raise HTTPException(status_code=401, detail="Credencial do nó inválida ou revogada.")


@router.post("/heartbeat", status_code=202)
def heartbeat(
    payload: NodeHeartbeat,
    node_token: str = Header(..., alias="X-Nivus-Node-Token", min_length=40, max_length=128),
):
    try:
        return process_node_heartbeat(
            node_token,
            payload.session_id,
            payload.sequence,
            payload.agent_version,
            payload.schema_version,
            payload.capabilities,
        )
    except NodeAuthenticationError:
        raise HTTPException(status_code=401, detail="Credencial ou sessão do nó inválida ou revogada.")
    except HeartbeatReplayError:
        raise HTTPException(status_code=409, detail="Heartbeat duplicado ou fora de ordem.")
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


@router.get("")
def get_nodes(admin: str = Depends(get_current_admin)):
    return list_nodes()


@router.delete("/{node_id}")
def delete_node(node_id: str, admin: str = Depends(get_current_admin)):
    if not revoke_node(node_id):
        raise HTTPException(status_code=404, detail="Nó ativo não encontrado.")
    return {"status": "revoked", "node_id": node_id}
