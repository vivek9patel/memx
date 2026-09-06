from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from memx.adapters.base import BaseMemoryAdapter
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
) -> StateDiff:
    pre = safe_export(adapter, entity_id, "pre_session")
    adapter.ingest_session(session)
    adapter.wait_until_ready(entity_id, timeout_s=ready_timeout)
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
) -> Iterator[QuestionEval]:
    evaluated = 0
    for case in cases:
        for session in case.sessions:
            if limit is not None and evaluated >= limit:
                return
            diff = ingest_session_diff(
                adapter,
                case.entity_id,
                session,
                snapshot_engine,
                ready_timeout,
            )
            questions = [
                q
                for q in case.questions
                if q.session_id == session.session_id
            ]
            if question_id is not None:
                questions = [q for q in questions if q.question_id == question_id]
            for question in questions:
                if limit is not None and evaluated >= limit:
                    return
                query_result = adapter.query(question.question_text, case.entity_id)
                candidate = build_candidate_answer(
                    question.question_text, query_result, synthesizer
                )
                verdict = judge.score(
                    question.question_text, question.gold_answer, candidate
                )
                diagnosis: DiagnosticResult | None = None
                if not verdict.passed:
                    diagnosis = classifier.classify(question, diff, query_result)
                evaluated += 1
                yield QuestionEval(
                    question=question,
                    case=case,
                    diff=diff,
                    verdict=verdict,
                    diagnosis=diagnosis,
                    candidate_answer=candidate,
                    query_result=query_result,
                )
