from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class FactStatus(StrEnum):
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    INVALIDATED = "invalidated"


class MemoryFact(BaseModel):
    model_config = ConfigDict(frozen=True)
    fact_id: str
    entity_id: str
    content: str
    status: FactStatus = FactStatus.ACTIVE
    supersedes: str | None = None  # fact_id this record replaced, if any
    created_at_turn: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class EntityState(BaseModel):
    """A full snapshot of everything an adapter knows about one entity_id at one point in time."""

    model_config = ConfigDict(frozen=True)
    entity_id: str
    facts: list[MemoryFact]
    snapshot_label: str  # e.g. "pre_ingest", "post_ingest"

    def facts_by_status(self, status: FactStatus) -> list[MemoryFact]:
        return [f for f in self.facts if f.status == status]

    def get_fact(self, fact_id: str) -> MemoryFact | None:
        return next((f for f in self.facts if f.fact_id == fact_id), None)
