from __future__ import annotations

from memx.adapters.mock import MockMemoryAdapter
from memx.cli.engine import evaluate_questions
from memx.diagnostics.classifier import DiagnosticClassifier
from memx.diagnostics.snapshot import StateSnapshotEngine
from memx.judge.litellm_judge import LiteLLMJudge
from memx.schemas.benchmark import BenchmarkCase, BenchmarkQuestion, QuestionCategory
from memx.schemas.session import Session, Speaker, Turn
from tests.test_cli.conftest import always_pass, mock_judge


class RecordingAdapter(MockMemoryAdapter):
    def __init__(self) -> None:
        super().__init__()
        self.calls: list[tuple[str, str]] = []

    def ingest_session(self, session: Session) -> None:
        self.calls.append(("ingest", session.session_id))
        super().ingest_session(session)

    def wait_until_ready(self, entity_id: str, timeout_s: float = 30.0, on_status=None) -> None:
        self.calls.append(("wait", entity_id))
        super().wait_until_ready(entity_id, timeout_s=timeout_s, on_status=on_status)


def _session(session_id: str, text: str) -> Session:
    return Session(
        session_id=session_id,
        entity_id="ent",
        turns=[Turn(turn_id=f"{session_id}-t1", speaker=Speaker.USER, content=text)],
        dataset_source="synthetic",
    )


def _question(question_id: str, session_id: str, text: str, gold: str) -> BenchmarkQuestion:
    return BenchmarkQuestion(
        question_id=question_id,
        entity_id="ent",
        session_id=session_id,
        question_text=text,
        gold_answer=gold,
        category=QuestionCategory.MULTI_HOP,
    )


def _three_session_case(*questions: BenchmarkQuestion) -> BenchmarkCase:
    return BenchmarkCase(
        case_id="c1",
        entity_id="ent",
        sessions=[
            _session("s1", "Caroline lives in Boston."),
            _session("s2", "Caroline works at Acme."),
            _session("s3", "Caroline has a cat."),
        ],
        questions=list(questions),
        dataset_source="synthetic",
    )


def _run(case: BenchmarkCase, adapter: RecordingAdapter, **kwargs):
    return list(
        evaluate_questions(
            cases=iter([case]),
            adapter=adapter,
            judge=LiteLLMJudge(),
            classifier=DiagnosticClassifier(relevance_fn=LiteLLMJudge().relevance_fn),
            snapshot_engine=StateSnapshotEngine(),
            synthesizer=None,
            ready_timeout=30.0,
            **kwargs,
        )
    )


def test_full_haystack_ingested_in_order_then_one_wait(monkeypatch) -> None:
    mock_judge(monkeypatch, always_pass)
    case = _three_session_case(
        _question("q-s3", "s3", "Where does Caroline live?", "Boston"),
    )
    adapter = RecordingAdapter()
    items = _run(case, adapter, limit=None)
    assert len(items) == 1
    assert adapter.calls == [
        ("ingest", "s1"),
        ("ingest", "s2"),
        ("ingest", "s3"),
        ("wait", "ent"),
    ]
    assert items[0].diff.pre_snapshot_label == "pre_ingest"
    assert items[0].diff.post_snapshot_label == "post_ingest"


def test_early_session_question_still_ingests_later_sessions(monkeypatch) -> None:
    mock_judge(monkeypatch, always_pass)
    case = _three_session_case(
        _question("q-s1", "s1", "Where does Caroline live?", "Boston"),
    )
    adapter = RecordingAdapter()
    items = _run(case, adapter, limit=None)
    assert len(items) == 1
    assert [sid for kind, sid in adapter.calls if kind == "ingest"] == ["s1", "s2", "s3"]
    assert adapter.calls[-1] == ("wait", "ent")
    contents = [
        entry.after.content
        for entry in items[0].diff.entries
        if entry.after is not None
    ]
    assert any("cat" in text for text in contents)


def test_question_ids_ingest_full_case_not_selected_session_only(monkeypatch) -> None:
    mock_judge(monkeypatch, always_pass)
    case = _three_session_case(
        _question("q-s1", "s1", "Where does Caroline live?", "Boston"),
        _question("q-s3", "s3", "Does Caroline have a cat?", "yes"),
    )
    adapter = RecordingAdapter()
    items = _run(case, adapter, limit=None, question_ids=["q-s1"])
    assert [item.question.question_id for item in items] == ["q-s1"]
    assert [sid for kind, sid in adapter.calls if kind == "ingest"] == ["s1", "s2", "s3"]


def test_limit_stops_scoring_but_ingests_full_current_case(monkeypatch) -> None:
    mock_judge(monkeypatch, always_pass)
    case = _three_session_case(
        _question("q-s1", "s1", "Where does Caroline live?", "Boston"),
        _question("q-s2", "s2", "Where does Caroline work?", "Acme"),
        _question("q-s3", "s3", "Does Caroline have a cat?", "yes"),
    )
    adapter = RecordingAdapter()
    items = _run(case, adapter, limit=1)
    assert [item.question.question_id for item in items] == ["q-s1"]
    assert [sid for kind, sid in adapter.calls if kind == "ingest"] == ["s1", "s2", "s3"]


def test_skip_ingest_queries_existing_store_without_ingest(monkeypatch) -> None:
    mock_judge(monkeypatch, always_pass)
    case = _three_session_case(
        _question("q-s3", "s3", "Where does Caroline live?", "Boston"),
    )
    adapter = RecordingAdapter()
    adapter.ingest_session(case.sessions[0])
    adapter.ingest_session(case.sessions[1])
    adapter.ingest_session(case.sessions[2])
    adapter.calls.clear()
    items = _run(case, adapter, limit=None, skip_ingest=True)
    assert len(items) == 1
    assert items[0].candidate_answer
    assert "Boston" in items[0].candidate_answer
    assert adapter.calls == []
    assert items[0].diff.entries
    assert all(entry.change_type == "added" for entry in items[0].diff.entries)
