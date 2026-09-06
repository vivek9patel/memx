from __future__ import annotations

from pathlib import Path

from memx.datasets.longmemeval import LongMemEvalLoader
from memx.datasets.registry import get_loader
from memx.schemas.benchmark import QuestionCategory

FIXTURES = Path(__file__).parent / "fixtures"
LME_SAMPLE = FIXTURES / "longmemeval_sample.json"


def test_longmemeval_loads_valid_cases_and_skips_malformed() -> None:
    loader = LongMemEvalLoader(LME_SAMPLE)
    cases = list(loader)
    assert len(cases) == 2
    assert loader.skipped_count == 1
    assert {case.case_id for case in cases} == {"lme-user-001", "lme-ku-002"}


def test_longmemeval_maps_question_types() -> None:
    cases = {case.case_id: case for case in LongMemEvalLoader(LME_SAMPLE)}
    assert cases["lme-user-001"].questions[0].category == QuestionCategory.SINGLE_HOP
    assert cases["lme-ku-002"].questions[0].category == QuestionCategory.CONTRADICTION


def test_longmemeval_question_session_ids_are_referential() -> None:
    for case in LongMemEvalLoader(LME_SAMPLE):
        session_ids = {session.session_id for session in case.sessions}
        for question in case.questions:
            assert question.session_id in session_ids


def test_longmemeval_knowledge_update_binds_to_answer_session() -> None:
    case = next(c for c in LongMemEvalLoader(LME_SAMPLE) if c.case_id == "lme-ku-002")
    assert case.questions[0].session_id == "sess-new"
    assert case.questions[0].evidence_turn_ids == ["sess-new_0"]


def test_get_loader_longmemeval() -> None:
    loader = get_loader("longmemeval", LME_SAMPLE)
    assert len(list(loader)) == 2
