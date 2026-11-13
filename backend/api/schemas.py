from typing import Literal

from pydantic import BaseModel, Field


class ActuatorCommand(BaseModel):
    topic: str = Field(min_length=1, max_length=128)
    command: str = Field(min_length=1, max_length=16)


class SettingUpdate(BaseModel):
    key: Literal["temp_threshold", "cpu_threshold"]
    value: str


class UserCreate(BaseModel):
    username: str = Field(min_length=1, max_length=32, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=12, max_length=256)
    role: Literal["admin", "viewer"]


class PasswordChange(BaseModel):
    username: str = Field(min_length=1, max_length=32)
    new_password: str = Field(min_length=12, max_length=256)
    admin_password: str = Field(min_length=1, max_length=256)
