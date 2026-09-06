from __future__ import annotations

import pytest

from memx.diagnostics.classifier import DiagnosticClassifier
from memx.diagnostics.snapshot import StateSnapshotEngine
from memx.diagnostics.taxonomy import FailureStage
from memx.schemas.benchmark import BenchmarkQuestion, QuestionCategory
from memx.schemas.query import QueryResult, RetrievedFact
from memx.schemas.state import EntityState, FactStatus, MemoryFact

ENTITY = "entity-alex"


def _question() -> BenchmarkQuestion:
    return BenchmarkQuestion(
        question_id="q-city",
        entity_id=ENTITY,
        session_id="s1",
        question_text="Where does Alex live?",
        gold_answer="Boston",
        category=QuestionCategory.SINGLE_HOP,
    )


def _relevance(_question: BenchmarkQuestion, content: str) -> bool:
    lowered = content.lower()
    return "boston" in lowered or "seattle" in lowered


def _fact(
    fact_id: str,
    content: str,
    *,
    status: FactStatus = FactStatus.ACTIVE,
    supersedes: str | None = None,
) -> MemoryFact:
    return MemoryFact(
        fact_id=fact_id,
        entity_id=ENTITY,
        content=content,
        status=status,
        supersedes=supersedes,
    )


def _state(label: str, facts: list[MemoryFact]) -> EntityState:
    return EntityState(entity_id=ENTITY, facts=facts, snapshot_label=label)


def _query(*fact_ids: str) -> QueryResult:
    return QueryResult(
        query_text="Where does Alex live?",
        entity_id=ENTITY,
        retrieved_facts=[
            RetrievedFact(fact_id=fid, content="placeholder") for fid in fact_ids
        ],
    )


@pytest.fixture
def classifier() -> DiagnosticClassifier:
    return DiagnosticClassifier(relevance_fn=_relevance)


@pytest.fixture
def engine() -> StateSnapshotEngine:
    return StateSnapshotEngine()


def test_stage_1_extraction(classifier: DiagnosticClassifier, engine: StateSnapshotEngine) -> None:
    pre = _state("pre_session", [])
    post = _state("post_session", [_fact("f-other", "Alex likes hiking.")])
    result = classifier.classify(_question(), engine.diff(pre, post), _query("f-other"))
    assert result.stage == FailureStage.STAGE_1_EXTRACTION


def test_stage_2_conflict_resolution(
    classifier: DiagnosticClassifier, engine: StateSnapshotEngine
) -> None:
    old = _fact("f-old", "Alex lives in Boston.")
    new = _fact("f-new", "Alex lives in Seattle.")
    pre = _state("pre_session", [old])
    post = _state("post_session", [old, new])
    result = classifier.classify(_question(), engine.diff(pre, post), _query("f-new"))
    assert result.stage == FailureStage.STAGE_2_CONFLICT_RESOLUTION


def test_stage_3_mutation(classifier: DiagnosticClassifier, engine: StateSnapshotEngine) -> None:
    old = _fact("f-old", "Alex lives in Boston.")
    new = _fact("f-new", "Alex lives in Seattle.", supersedes="f-old")
    pre = _state("pre_session", [old])
    post = _state("post_session", [old, new])
    result = classifier.classify(_question(), engine.diff(pre, post), _query("f-new"))
    assert result.stage == FailureStage.STAGE_3_MUTATION


def test_stage_4_retrieval(classifier: DiagnosticClassifier, engine: StateSnapshotEngine) -> None:
    old = _fact("f-old", "Alex lives in Boston.", status=FactStatus.INVALIDATED)
    new = _fact("f-new", "Alex lives in Seattle.", supersedes="f-old")
    pre = _state("pre_session", [old])
    post = _state("post_session", [old, new])
    result = classifier.classify(_question(), engine.diff(pre, post), _query())
    assert result.stage == FailureStage.STAGE_4_RETRIEVAL


def test_no_failure_synthesis_issue(
    classifier: DiagnosticClassifier, engine: StateSnapshotEngine
) -> None:
    old = _fact("f-old", "Alex lives in Boston.", status=FactStatus.INVALIDATED)
    new = _fact("f-new", "Alex lives in Seattle.", supersedes="f-old")
    pre = _state("pre_session", [old])
    post = _state("post_session", [old, new])
    result = classifier.classify(_question(), engine.diff(pre, post), _query("f-new"))
    assert result.stage == FailureStage.NO_FAILURE


def test_diff_rejects_mismatched_entities(engine: StateSnapshotEngine) -> None:
    pre = EntityState(entity_id="a", facts=[], snapshot_label="pre")
    post = EntityState(entity_id="b", facts=[], snapshot_label="post")
    with pytest.raises(ValueError, match="different entities"):
        engine.diff(pre, post)


def test_diff_identical_states_are_unchanged(engine: StateSnapshotEngine) -> None:
    fact = _fact("f1", "Alex lives in Boston.")
    pre = _state("pre_session", [fact])
    post = _state("post_session", [fact])
    diff = engine.diff(pre, post)
    assert all(entry.change_type == "unchanged" for entry in diff.entries)
    assert len(diff.entries) == 1
