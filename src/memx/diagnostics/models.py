from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from memx.diagnostics.taxonomy import FailureStage
from memx.schemas.state import MemoryFact


class FactDiffEntry(BaseModel):
    model_config = ConfigDict(frozen=True)
    fact_id: str
    change_type: str  # "added" | "removed" | "status_changed" | "content_changed" | "unchanged"
    before: MemoryFact | None = None
    after: MemoryFact | None = None


class StateDiff(BaseModel):
    model_config = ConfigDict(frozen=True)
    entity_id: str
    pre_snapshot_label: str
    post_snapshot_label: str
    entries: list[FactDiffEntry]

    @property
    def added(self) -> list[FactDiffEntry]:
        return [e for e in self.entries if e.change_type == "added"]

    @property
    def status_changed(self) -> list[FactDiffEntry]:
        return [e for e in self.entries if e.change_type == "status_changed"]


class DiagnosticResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    question_id: str
    stage: FailureStage
    rationale: str
    supporting_diff_entries: list[FactDiffEntry] = Field(default_factory=list)
    retrieved_fact_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
