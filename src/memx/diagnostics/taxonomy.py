from __future__ import annotations

from enum import IntEnum


class FailureStage(IntEnum):
    STAGE_1_EXTRACTION = 1  # fact never parsed into the DB at all
    STAGE_2_CONFLICT_RESOLUTION = 2  # fact extracted, but contradiction vs. existing node undetected
    STAGE_3_MUTATION = 3  # contradiction detected, but old record never invalidated/deprecated
    STAGE_4_RETRIEVAL = 4  # DB state fully correct; retriever returned the wrong/stale record
    NO_FAILURE = 0  # judge marked PASS; classifier should not be invoked


FAILURE_STAGE_LABELS: dict[FailureStage, str] = {
    FailureStage.STAGE_1_EXTRACTION: "Extraction Failure",
    FailureStage.STAGE_2_CONFLICT_RESOLUTION: "Conflict Resolution Failure",
    FailureStage.STAGE_3_MUTATION: "Mutation Failure",
    FailureStage.STAGE_4_RETRIEVAL: "Retrieval Failure",
    FailureStage.NO_FAILURE: "No Failure",
}
