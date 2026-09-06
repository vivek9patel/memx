from __future__ import annotations

import json
from pathlib import Path

import pytest

from memx.datasets.locomo import LocomoLoader
from memx.datasets.registry import get_loader
from memx.exceptions import MemxError
from memx.schemas.benchmark import QuestionCategory
from memx.schemas.session import Speaker

FIXTURES = Path(__file__).parent / "fixtures"
LOCOMO_SAMPLE = FIXTURES / "locomo_sample.json"


def test_locomo_loads_valid_cases_and_skips_malformed() -> None:
    loader = LocomoLoader(LOCOMO_SAMPLE)
    cases = list(loader)
    assert len(cases) == 2
    assert loader.skipped_count == 1
    assert {case.case_id for case in cases} == {"conv-caroline", "conv-jon"}


def test_locomo_maps_category_codes() -> None:
    loader = LocomoLoader(LOCOMO_SAMPLE)
    cases = {case.case_id: case for case in loader}
    questions = {q.question_id: q for q in cases["conv-caroline"].questions}
    assert questions["conv-caroline_q0000"].category == QuestionCategory.SINGLE_HOP
    assert questions["conv-caroline_q0001"].category == QuestionCategory.MULTI_HOP
    assert cases["conv-jon"].questions[0].category == QuestionCategory.TEMPORAL


def test_locomo_default_speakers_are_user() -> None:
    case = next(iter(LocomoLoader(LOCOMO_SAMPLE)))
    assert all(turn.speaker == Speaker.USER for session in case.sessions for turn in session.turns)


def test_locomo_speaker_role_map() -> None:
    loader = LocomoLoader(
        LOCOMO_SAMPLE,
        speaker_role_map={"Melanie": Speaker.ASSISTANT},
    )
    case = next(c for c in loader if c.case_id == "conv-caroline")
    speakers = {(t.metadata["speaker_name"], t.speaker) for s in case.sessions for t in s.turns}
    assert ("Caroline", Speaker.USER) in speakers
    assert ("Melanie", Speaker.ASSISTANT) in speakers


def test_locomo_question_session_ids_are_referential() -> None:
    for case in LocomoLoader(LOCOMO_SAMPLE):
        session_ids = {session.session_id for session in case.sessions}
        for question in case.questions:
            assert question.session_id in session_ids


def test_locomo_unrecognized_category_raises(tmp_path: Path) -> None:
    path = tmp_path / "bad_category.json"
    path.write_text(
        json.dumps(
            [
                {
                    "sample_id": "x",
                    "conversation": {
                        "speaker_a": "A",
                        "speaker_b": "B",
                        "session_1": [{"speaker": "A", "dia_id": "D1:1", "text": "hello"}],
                    },
                    "qa": [
                        {
                            "question": "What?",
                            "answer": "hello",
                            "evidence": ["D1:1"],
                            "category": 99,
                        }
                    ],
                }
            ]
        ),
        encoding="utf-8",
    )
    loader = LocomoLoader(path)
    with pytest.raises(MemxError, match="Unknown LoCoMo category code: 99"):
        list(loader)


def test_locomo_malformed_json_raises(tmp_path: Path) -> None:
    path = tmp_path / "broken.json"
    path.write_text("{not-json", encoding="utf-8")
    with pytest.raises(MemxError, match="not a JSON array"):
        LocomoLoader(path)


def test_get_loader_unknown_dataset_raises() -> None:
    with pytest.raises(MemxError, match="Unknown dataset"):
        get_loader("nonexistent", LOCOMO_SAMPLE)


def test_get_loader_locomo_roundtrip() -> None:
    loader = get_loader("locomo", LOCOMO_SAMPLE)
    cases = list(loader)
    assert len(cases) > 0
    assert loader.skipped_count == 1
