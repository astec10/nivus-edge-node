import ipaddress
import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator


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
