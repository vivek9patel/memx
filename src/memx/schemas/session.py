from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Speaker(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


def _require_non_empty(value: str, field_name: str) -> str:
    if not value.strip():
        raise ValueError(f"{field_name} must not be empty or whitespace-only")
    return value


class Turn(BaseModel):
    model_config = ConfigDict(frozen=True)
    turn_id: str
    speaker: Speaker
    content: str
    timestamp: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("turn_id")
    @classmethod
    def turn_id_not_empty(cls, v: str) -> str:
        return _require_non_empty(v, "Turn.turn_id")

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Turn.content must not be empty or whitespace-only")
        return v


class Session(BaseModel):
    model_config = ConfigDict(frozen=True)
    session_id: str
    entity_id: str  # the user/agent identity the memory is scoped to
    turns: list[Turn]
    dataset_source: str  # e.g. "locomo", "longmemeval", "synthetic"
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("session_id")
    @classmethod
    def session_id_not_empty(cls, v: str) -> str:
        return _require_non_empty(v, "Session.session_id")

    @field_validator("entity_id")
    @classmethod
    def entity_id_not_empty(cls, v: str) -> str:
        return _require_non_empty(v, "Session.entity_id")

    @field_validator("turns")
    @classmethod
    def turns_not_empty(cls, v: list[Turn]) -> list[Turn]:
        if not v:
            raise ValueError("Session must contain at least one turn")
        return v
