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


def test_preceding_sessions_ingest_in_parallel_then_wait_once(monkeypatch) -> None:
    mock_judge(monkeypatch, always_pass)
    case = BenchmarkCase(
        case_id="c1",
        entity_id="ent",
        sessions=[
            _session("s1", "Caroline lives in Boston."),
            _session("s2", "Caroline works at Acme."),
            _session("s3", "Caroline has a cat."),
        ],
        questions=[
            BenchmarkQuestion(
                question_id="q-s3",
                entity_id="ent",
                session_id="s3",
                question_text="Where does Caroline live?",
                gold_answer="Boston",
                category=QuestionCategory.MULTI_HOP,
            )
        ],
        dataset_source="synthetic",
    )
    adapter = RecordingAdapter()
    items = list(
        evaluate_questions(
            cases=iter([case]),
            adapter=adapter,
            judge=LiteLLMJudge(),
            classifier=DiagnosticClassifier(relevance_fn=LiteLLMJudge().relevance_fn),
            snapshot_engine=StateSnapshotEngine(),
            synthesizer=None,
            ready_timeout=30.0,
            limit=None,
        )
    )
    assert len(items) == 1
    kinds = [kind for kind, _ in adapter.calls]
    assert kinds.count("ingest") == 3
    assert kinds.count("wait") == 2
    preceding = {sid for kind, sid in adapter.calls[:2] if kind == "ingest"}
    assert preceding == {"s1", "s2"}
    assert adapter.calls[2] == ("wait", "ent")
    assert adapter.calls[3] == ("ingest", "s3")
    assert adapter.calls[4] == ("wait", "ent")


def test_skip_ingest_queries_existing_store_without_ingest(monkeypatch) -> None:
    mock_judge(monkeypatch, always_pass)
    case = BenchmarkCase(
        case_id="c1",
        entity_id="ent",
        sessions=[
            _session("s1", "Caroline lives in Boston."),
            _session("s2", "Caroline works at Acme."),
            _session("s3", "Caroline has a cat."),
        ],
        questions=[
            BenchmarkQuestion(
                question_id="q-s3",
                entity_id="ent",
                session_id="s3",
                question_text="Where does Caroline live?",
                gold_answer="Boston",
                category=QuestionCategory.MULTI_HOP,
            )
        ],
        dataset_source="synthetic",
    )
    adapter = RecordingAdapter()
    adapter.ingest_session(case.sessions[0])
    adapter.ingest_session(case.sessions[1])
    adapter.ingest_session(case.sessions[2])
    adapter.calls.clear()
    items = list(
        evaluate_questions(
            cases=iter([case]),
            adapter=adapter,
            judge=LiteLLMJudge(),
            classifier=DiagnosticClassifier(relevance_fn=LiteLLMJudge().relevance_fn),
            snapshot_engine=StateSnapshotEngine(),
            synthesizer=None,
            ready_timeout=30.0,
            limit=None,
            skip_ingest=True,
        )
    )
    assert len(items) == 1
    assert items[0].candidate_answer
    assert "Boston" in items[0].candidate_answer
    assert adapter.calls == []
    assert items[0].diff.entries
    assert all(entry.change_type == "added" for entry in items[0].diff.entries)

