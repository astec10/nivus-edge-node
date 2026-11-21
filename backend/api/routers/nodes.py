from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StrictFloat, StrictInt, StrictStr, field_validator, model_validator

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
    normalize_node_name,
)
from services.node_telemetry import (
    MAX_TELEMETRY_SAMPLES,
    MAX_TELEMETRY_HISTORY_OFFSET,
    TelemetryRateLimitError,
    TELEMETRY_SCHEMA_VERSION,
    get_node_telemetry_history_page,
    normalize_telemetry_samples,
    process_node_telemetry,
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
    name: str = Field(min_length=1, max_length=64)

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        try:
            return normalize_node_name(value)
        except ValueError as error:
            raise ValueError(str(error)) from error


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


class NodeTelemetrySample(BaseModel):
    model_config = ConfigDict(extra="forbid")
    metric: StrictStr = Field(min_length=1, max_length=64)
    value: StrictInt | StrictFloat | None
    unit: StrictStr = Field(min_length=1, max_length=16)
    quality: Literal["measured", "estimated", "unavailable"]

    @model_validator(mode="after")
    def validate_metric_sample(self):
        normalize_telemetry_samples([self.model_dump()])
        return self


class NodeTelemetryEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_id: str = Field(min_length=40, max_length=128, pattern=r"^[A-Za-z0-9_-]+$")
    sequence: StrictInt = Field(ge=0, le=2**63 - 1)
    schema_version: StrictInt = Field(ge=TELEMETRY_SCHEMA_VERSION, le=TELEMETRY_SCHEMA_VERSION)
    observed_at: AwareDatetime
    samples: list[NodeTelemetrySample] = Field(min_length=1, max_length=MAX_TELEMETRY_SAMPLES)

    @field_validator("samples")
    @classmethod
    def samples_are_unique(cls, value: list[NodeTelemetrySample]) -> list[NodeTelemetrySample]:
        names = [sample.metric for sample in value]
        if len(set(names)) != len(names):
            raise ValueError("A amostra contém métricas duplicadas.")
        return value

    @field_validator("schema_version")
    @classmethod
    def supported_schema_version(cls, value: int) -> int:
        if type(value) is not int or value != TELEMETRY_SCHEMA_VERSION:
            raise ValueError("Versão de esquema de telemetria não suportada.")
        return value


class NodeTelemetryQueryResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    node_id: str
    schema_version: int
    observed_at: str
    received_at: str
    clock_skew_seconds: float
    samples: list[NodeTelemetrySample]


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


@router.post("/telemetry", status_code=202)
def ingest_telemetry(
    payload: NodeTelemetryEnvelope,
    node_token: str = Header(..., alias="X-Nivus-Node-Token", min_length=40, max_length=128),
):
    try:
        return process_node_telemetry(
            node_token,
            payload.session_id,
            payload.sequence,
            payload.schema_version,
            payload.observed_at,
            [sample.model_dump() for sample in payload.samples],
        )
    except NodeAuthenticationError:
        raise HTTPException(status_code=401, detail="Credencial ou sessão do nó inválida ou revogada.")
    except HeartbeatReplayError:
        raise HTTPException(status_code=409, detail="Mensagem do nó duplicada ou fora de ordem.")
    except TelemetryRateLimitError as error:
        raise HTTPException(
            status_code=429,
            detail=str(error),
            headers={"Retry-After": str(error.retry_after_seconds)},
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


@router.get("")
def get_nodes(admin: str = Depends(get_current_admin)):
    return list_nodes()


@router.get("/{node_id}/telemetry", response_model=list[NodeTelemetryQueryResult])
def get_node_telemetry(
    node_id: str,
    response: Response,
    since: AwareDatetime | None = Query(default=None),
    limit: int = Query(default=120, ge=1, le=500),
    offset: int = Query(default=0, ge=0, le=MAX_TELEMETRY_HISTORY_OFFSET),
    snapshot_until: AwareDatetime | None = Query(default=None),
    admin: str = Depends(get_current_admin),
):
    try:
        page = get_node_telemetry_history_page(
            node_id,
            since=since,
            limit=limit,
            offset=offset,
            snapshot_until=snapshot_until,
        )
        response.headers["X-Nivus-History-Pagination"] = "offset-v1"
        response.headers["X-Nivus-History-Total-Batches"] = str(page["total_batches"])
        response.headers["X-Nivus-History-Offset"] = str(page["offset"])
        response.headers["X-Nivus-History-Limit"] = str(page["limit"])
        response.headers["X-Nivus-History-Has-More"] = "true" if page["has_more"] else "false"
        if page["range_start"] is not None:
            response.headers["X-Nivus-History-Range-Start"] = page["range_start"]
        if page["range_end"] is not None:
            response.headers["X-Nivus-History-Range-End"] = page["range_end"]
        if page["snapshot_until"] is not None:
            response.headers["X-Nivus-History-Snapshot-Until"] = page["snapshot_until"]
        return page["batches"]
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


@router.delete("/{node_id}")
def delete_node(node_id: str, admin: str = Depends(get_current_admin)):
    if not revoke_node(node_id):
        raise HTTPException(status_code=404, detail="Nó ativo não encontrado.")
    return {"status": "revoked", "node_id": node_id}
