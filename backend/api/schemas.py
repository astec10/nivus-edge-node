from typing import Literal

from pydantic import BaseModel, Field, field_validator


def validate_password_policy(value: str) -> str:
    if not any(character.isalpha() for character in value):
        raise ValueError("A senha deve conter pelo menos uma letra.")
    if not any(character.isdigit() for character in value):
        raise ValueError("A senha deve conter pelo menos um número.")
    return value


class ActuatorCommand(BaseModel):
    topic: str = Field(min_length=1, max_length=128)
    command: str = Field(min_length=1, max_length=16)


class SettingUpdate(BaseModel):
    key: Literal["temp_threshold", "cpu_threshold"]
    value: str


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
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=8, max_length=256)

    @field_validator("new_password")
    @classmethod
    def password_has_letter_and_number(cls, value: str) -> str:
        return validate_password_policy(value)
