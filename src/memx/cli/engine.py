from __future__ import annotations

from collections.abc import Callable, Collection, Iterator
from dataclasses import dataclass

from memx.adapters.base import BaseMemoryAdapter
from memx.adapters.poll import run_parallel
from memx.cli.answer_builder import build_candidate_answer
from memx.diagnostics.classifier import DiagnosticClassifier
from memx.diagnostics.models import DiagnosticResult, StateDiff
from memx.diagnostics.snapshot import StateSnapshotEngine
from memx.exceptions import AdapterError
from memx.judge.litellm_judge import LiteLLMJudge, JudgeVerdict
from memx.schemas.benchmark import BenchmarkCase, BenchmarkQuestion
from memx.schemas.query import QueryResult
from memx.schemas.session import Session
from memx.schemas.state import EntityState
from memx.synthesis.litellm_answer import LiteLLMAnswerSynthesizer


@dataclass(frozen=True)
class QuestionEval:
    question: BenchmarkQuestion
    case: BenchmarkCase
    diff: StateDiff
    verdict: JudgeVerdict
    diagnosis: DiagnosticResult | None
    candidate_answer: str
    query_result: QueryResult


def safe_export(adapter: BaseMemoryAdapter, entity_id: str, label: str) -> EntityState:
    try:
        state = adapter.export_state(entity_id)
    except AdapterError:
        return EntityState(entity_id=entity_id, facts=[], snapshot_label=label)
    return EntityState(
        entity_id=state.entity_id,
        facts=list(state.facts),
        snapshot_label=label,
    )


def ingest_session_diff(
    adapter: BaseMemoryAdapter,
    entity_id: str,
    session,
    snapshot_engine: StateSnapshotEngine,
    ready_timeout: float,
    on_status: Callable[[str], None] | None = None,
) -> StateDiff:
    name = getattr(adapter, "adapter_name", "adapter")
    _emit(on_status, f"Snapshot before {session.session_id}")
    pre = safe_export(adapter, entity_id, "pre_session")
    _emit(on_status, f"Ingesting {session.session_id} via {name}")
    adapter.ingest_session(session)
    _emit(on_status, f"Waiting on {name} ({entity_id})")
    adapter.wait_until_ready(entity_id, timeout_s=ready_timeout, on_status=on_status)
    _emit(on_status, f"Snapshot after {session.session_id}")
    post = safe_export(adapter, entity_id, "post_session")
    return snapshot_engine.diff(pre, post)


def evaluate_questions(
    *,
    cases: Iterator[BenchmarkCase],
    adapter: BaseMemoryAdapter,
    judge: LiteLLMJudge,
    classifier: DiagnosticClassifier,
    snapshot_engine: StateSnapshotEngine,
    synthesizer: LiteLLMAnswerSynthesizer | None,
    ready_timeout: float,
    limit: int | None,
    question_id: str | None = None,
    question_ids: Collection[str] | None = None,
    on_status: Callable[[str], None] | None = None,
    skip_ingest: bool = False,
) -> Iterator[QuestionEval]:
    evaluated = 0
    selected = None if question_ids is None else frozenset(question_ids)
    for case in cases:
        if skip_ingest:
            questions = _selected_questions(case, question_id, selected)
            if not questions:
                continue
            if limit is not None and evaluated >= limit:
                return
            diff = _existing_state_diff(
                adapter, case.entity_id, snapshot_engine, on_status=on_status
            )
            for item in _score_questions(
                questions,
                case=case,
                adapter=adapter,
                judge=judge,
                classifier=classifier,
                synthesizer=synthesizer,
                diff=diff,
                on_status=on_status,
                empty_on_query_error=True,
            ):
                if limit is not None and evaluated >= limit:
                    return
                evaluated += 1
                yield item
            continue
        if selected is not None:
            needed_sessions = {
                question.session_id
                for question in case.questions
                if question.question_id in selected
            }
            if not needed_sessions:
                continue
            sessions = _sessions_through(case.sessions, needed_sessions)
        else:
            sessions = case.sessions
        queued: list[Session] = []
        for session in sessions:
            if limit is not None and evaluated >= limit:
                return
            questions = [
                q
                for q in case.questions
                if q.session_id == session.session_id
            ]
            if question_id is not None:
                questions = [q for q in questions if q.question_id == question_id]
            if selected is not None:
                questions = [q for q in questions if q.question_id in selected]
            if not questions:
                queued.append(session)
                continue
            _flush_queued_ingests(
                adapter,
                case.entity_id,
                queued,
                ready_timeout,
                on_status=on_status,
            )
            queued = []
            diff = ingest_session_diff(
                adapter,
                case.entity_id,
                session,
                snapshot_engine,
                ready_timeout,
                on_status=on_status,
            )
            for item in _score_questions(
                questions,
                case=case,
                adapter=adapter,
                judge=judge,
                classifier=classifier,
                synthesizer=synthesizer,
                diff=diff,
                on_status=on_status,
            ):
                if limit is not None and evaluated >= limit:
                    return
                evaluated += 1
                yield item
        _flush_queued_ingests(
            adapter,
            case.entity_id,
            queued,
            ready_timeout,
            on_status=on_status,
        )


def _existing_state_diff(
    adapter: BaseMemoryAdapter,
    entity_id: str,
    snapshot_engine: StateSnapshotEngine,
    on_status: Callable[[str], None] | None = None,
) -> StateDiff:
    _emit(on_status, f"Snapshot existing store ({entity_id})")
    pre = EntityState(entity_id=entity_id, facts=[], snapshot_label="pre_existing")
    post = safe_export(adapter, entity_id, "current")
    return snapshot_engine.diff(pre, post)


def _selected_questions(
    case: BenchmarkCase,
    question_id: str | None,
    selected: frozenset[str] | None,
) -> list[BenchmarkQuestion]:
    questions = list(case.questions)
    if question_id is not None:
        questions = [q for q in questions if q.question_id == question_id]
    if selected is not None:
        questions = [q for q in questions if q.question_id in selected]
    return questions


def _score_questions(
    questions: list[BenchmarkQuestion],
    *,
    case: BenchmarkCase,
    adapter: BaseMemoryAdapter,
    judge: LiteLLMJudge,
    classifier: DiagnosticClassifier,
    synthesizer: LiteLLMAnswerSynthesizer | None,
    diff: StateDiff,
    on_status: Callable[[str], None] | None,
    empty_on_query_error: bool = False,
) -> Iterator[QuestionEval]:
    for question in questions:
        _emit(on_status, f"Query {question.question_id}")
        query_result = _query(
            adapter,
            question.question_text,
            case.entity_id,
            empty_on_error=empty_on_query_error,
        )
        _emit(on_status, f"Synthesize {question.question_id}")
        candidate = build_candidate_answer(
            question.question_text, query_result, synthesizer
        )
        _emit(on_status, f"Judge {question.question_id}")
        verdict = judge.score(
            question.question_text, question.gold_answer, candidate
        )
        diagnosis: DiagnosticResult | None = None
        if not verdict.passed:
            _emit(on_status, f"Diagnose {question.question_id}")
            diagnosis = classifier.classify(question, diff, query_result)
        yield QuestionEval(
            question=question,
            case=case,
            diff=diff,
            verdict=verdict,
            diagnosis=diagnosis,
            candidate_answer=candidate,
            query_result=query_result,
        )


def _flush_queued_ingests(
    adapter: BaseMemoryAdapter,
    entity_id: str,
    queued: list[Session],
    ready_timeout: float,
    on_status: Callable[[str], None] | None = None,
) -> None:
    if not queued:
        return
    name = getattr(adapter, "adapter_name", "adapter")
    labels = ", ".join(session.session_id for session in queued)
    _emit(on_status, f"Queue ingest {len(queued)} sessions via {name} ({labels})")
    run_parallel(adapter.ingest_session, queued)
    _emit(on_status, f"Waiting on {name} ({entity_id})")
    adapter.wait_until_ready(entity_id, timeout_s=ready_timeout, on_status=on_status)


def _sessions_through(sessions: list[Session], needed_ids: Collection[str]) -> list[Session]:
    last = -1
    for index, session in enumerate(sessions):
        if session.session_id in needed_ids:
            last = index
    if last < 0:
        return []
    return sessions[: last + 1]


def _query(
    adapter: BaseMemoryAdapter,
    query_text: str,
    entity_id: str,
    *,
    empty_on_error: bool,
) -> QueryResult:
    try:
        return adapter.query(query_text, entity_id)
    except AdapterError:
        if empty_on_error:
            return QueryResult(
                query_text=query_text,
                entity_id=entity_id,
                retrieved_facts=[],
                latency_ms=0.0,
            )
        raise


def _emit(on_status: Callable[[str], None] | None, message: str) -> None:
    if on_status is not None:
        on_status(message)
