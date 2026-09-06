from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from memx.schemas.session import Session


class QuestionCategory(StrEnum):
    SINGLE_HOP = "single_hop"
    MULTI_HOP = "multi_hop"
    TEMPORAL = "temporal"
    CONTRADICTION = "contradiction"  # tests conflict resolution / mutation directly
    OPEN_DOMAIN = "open_domain"
    ADVERSARIAL = "adversarial"


class BenchmarkQuestion(BaseModel):
    model_config = ConfigDict(frozen=True)
    question_id: str
    entity_id: str
    session_id: str  # which Session this question is evaluated against
    question_text: str
    gold_answer: str
    category: QuestionCategory
    evidence_turn_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class BenchmarkCase(BaseModel):
    """One fully-linked unit: the conversational session(s) plus the questions asked about them."""

    model_config = ConfigDict(frozen=True)
    case_id: str
    entity_id: str
    sessions: list[Session]
    questions: list[BenchmarkQuestion]
    dataset_source: str
