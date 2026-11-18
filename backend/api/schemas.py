import ipaddress
import re
from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator


def validate_password_policy(value: str) -> str:
    if not any(character.isalpha() for character in value):
        raise ValueError("A senha deve conter pelo menos uma letra.")
    if not any(character in "0123456789" for character in value):
        raise ValueError("A senha deve conter pelo menos um número.")
    return value


class ActuatorCommand(BaseModel):
    topic: str = Field(min_length=1, max_length=128)
    command: str = Field(min_length=1, max_length=16)


class SettingUpdate(BaseModel):
    key: Literal["temp_threshold", "cpu_threshold"]
    value: str


class TimeSyncUpdate(BaseModel):
    servers: list[str] = Field(min_length=3, max_length=3)

    @field_validator("servers")
    @classmethod
    def validate_servers(cls, value: list[str]) -> list[str]:
        label = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
        normalized = []
        for item in value:
            host = item.strip().lower().rstrip(".")
            try:
                ipaddress.ip_address(host)
            except ValueError:
                pass
            else:
                raise ValueError("Use nomes DNS, não endereços IP.")
            if (
                not host
                or len(host) > 253
                or any(not label.fullmatch(part) for part in host.split("."))
            ):
                raise ValueError("Use nomes DNS sem URL, porta ou espaços internos.")
            normalized.append(host)
        if len(set(normalized)) != 3:
            raise ValueError("Os três servidores NTP precisam ser diferentes.")
        return normalized


class MaintenanceUpdate(BaseModel):
    enabled: bool


class UserCreate(BaseModel):
    username: str = Field(min_length=1, max_length=32, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=8, max_length=256)
    role: Literal["admin", "viewer"]

    @field_validator("password")
    @classmethod
    def password_has_letter_and_number(cls, value: str) -> str:
        return validate_password_policy(value)


class PasswordChange(BaseModel):
    username: str = Field(min_length=1, max_length=32)
    new_password: str = Field(min_length=8, max_length=256)
    admin_password: str = Field(min_length=1, max_length=256)

    @field_validator("new_password")
    @classmethod
    def password_has_letter_and_number(cls, value: str) -> str:
        return validate_password_policy(value)


class PasswordRotation(BaseModel):
    new_password: str = Field(min_length=8, max_length=256)

    @field_validator("new_password")
    @classmethod
    def password_has_letter_and_number(cls, value: str) -> str:
        return validate_password_policy(value)


ProviderDataClass = Literal[
    "public", "synthetic", "operational", "personal", "home", "camera"
]


class AIProviderCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_type: Literal["openai", "anthropic", "gemini", "ollama", "manual"]
    name: str = Field(min_length=1, max_length=80)
    protocol: Literal["openai-compatible", "anthropic", "gemini", "ollama"] = "openai-compatible"
    endpoint_scope: Literal["cloud", "local"] = "cloud"
    base_url: str = Field(min_length=1, max_length=512)
    model_name: str = Field(min_length=1, max_length=128)
    responsible: str = Field(min_length=1, max_length=80)
    purpose: str = Field(min_length=1, max_length=500)
    auth_method: Literal["none", "bearer", "x-api-key", "google-api-key"] = "none"
    api_key: SecretStr | None = Field(default=None, max_length=4096)
    monthly_budget_usd: float | None = Field(default=None, ge=0, le=100000)
    input_cost_per_million_usd: float | None = Field(default=None, ge=0, le=10000)
    output_cost_per_million_usd: float | None = Field(default=None, ge=0, le=10000)
    pricing_verified_on: date | None = None
    max_requests_per_hour: int = Field(default=30, ge=1, le=10000)
    timeout_seconds: int = Field(default=10, ge=2, le=60)
    allowed_data_classes: list[ProviderDataClass] = Field(
        default_factory=lambda: ["public", "synthetic"], max_length=6
    )

    @field_validator("name", "model_name", "responsible", "purpose", "base_url")
    @classmethod
    def trim_provider_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized or any(ord(char) < 32 for char in normalized):
            raise ValueError("O campo não pode ficar vazio ou conter caracteres de controle.")
        return normalized

    @field_validator("allowed_data_classes")
    @classmethod
    def provider_data_classes_are_unique(cls, value: list[ProviderDataClass]) -> list[ProviderDataClass]:
        if len(set(value)) != len(value):
            raise ValueError("A classificação de dados contém valores repetidos.")
        return value


class AIProviderUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=80)
    model_name: str | None = Field(default=None, min_length=1, max_length=128)
    responsible: str | None = Field(default=None, min_length=1, max_length=80)
    purpose: str | None = Field(default=None, min_length=1, max_length=500)
    monthly_budget_usd: float | None = Field(default=None, ge=0, le=100000)
    input_cost_per_million_usd: float | None = Field(default=None, ge=0, le=10000)
    output_cost_per_million_usd: float | None = Field(default=None, ge=0, le=10000)
    pricing_verified_on: date | None = None
    max_requests_per_hour: int | None = Field(default=None, ge=1, le=10000)
    timeout_seconds: int | None = Field(default=None, ge=2, le=60)
    allowed_data_classes: list[ProviderDataClass] | None = Field(default=None, max_length=6)

    @field_validator("name", "model_name", "responsible", "purpose")
    @classmethod
    def trim_optional_provider_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized or any(ord(char) < 32 for char in normalized):
            raise ValueError("O campo não pode ficar vazio ou conter caracteres de controle.")
        return normalized

    @field_validator("allowed_data_classes")
    @classmethod
    def updated_data_classes_are_unique(
        cls, value: list[ProviderDataClass] | None
    ) -> list[ProviderDataClass] | None:
        if value is not None and len(set(value)) != len(value):
            raise ValueError("A classificação de dados contém valores repetidos.")
        return value


class AIProviderCredentialUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    api_key: SecretStr = Field(min_length=1, max_length=4096)


class AIProviderEnabled(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool


class AIExecutorRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: UUID
    task_id: str = Field(min_length=8, max_length=64, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{7,63}$")
    provider_id: str = Field(min_length=32, max_length=32, pattern=r"^[a-f0-9]{32}$")
    prompt: str = Field(min_length=1, max_length=12000)
    data_class: ProviderDataClass
    task_budget_usd: float = Field(default=0, ge=0, le=100000)
    max_output_tokens: int = Field(default=1024, ge=1, le=2048)

    @field_validator("prompt")
    @classmethod
    def prompt_must_contain_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("A instrução não pode ficar vazia.")
        return value
