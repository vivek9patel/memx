from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RetrievedFact(BaseModel):
    model_config = ConfigDict(frozen=True)
    fact_id: str
    content: str
    score: float | None = None
    source_turn_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class QueryResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    query_text: str
    entity_id: str
    retrieved_facts: list[RetrievedFact]
    raw_answer: str | None = None  # if the adapter does answer synthesis itself
    latency_ms: float | None = None
