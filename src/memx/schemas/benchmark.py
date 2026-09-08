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
    session_id: str  # evidence / answer session (metadata); ingest uses the full case haystack
    question_text: str
    gold_answer: str
    category: QuestionCategory
    evidence_turn_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class BenchmarkCase(BaseModel):
    """One fully-linked unit: the complete official history plus questions about it.

    ``sessions`` is the haystack the harness always ingests (LoCoMo conversation,
    LongMemEval haystack, or a shorter list if the dataset is an oracle subset).
    Sampling flags choose which ``questions`` to score, not which sessions to drop.
    """

    model_config = ConfigDict(frozen=True)
    case_id: str
    entity_id: str
    sessions: list[Session]
    questions: list[BenchmarkQuestion]
    dataset_source: str
