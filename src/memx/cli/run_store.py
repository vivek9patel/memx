from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from memx.cli.engine import QuestionEval
from memx.diagnostics.models import DiagnosticResult, StateDiff
from memx.exceptions import MemxError

_LAST_RUN_RELATIVE = Path(".memx") / "last_run.json"


def last_run_path() -> Path:
    return Path.cwd() / _LAST_RUN_RELATIVE


class SavedQuestion(BaseModel):
    model_config = ConfigDict(frozen=True)
    question_id: str
    question_text: str
    gold_answer: str
    candidate_answer: str
    judge_verdict: str
    judge_reasoning: str
    retrieved_facts: list[str]
    diff: StateDiff
    diagnosis: DiagnosticResult | None = None


class SavedRun(BaseModel):
    model_config = ConfigDict(frozen=True)
    created_at: str
    dataset: str
    source: str
    adapter: str
    questions: list[SavedQuestion]


def record_from_eval(item: QuestionEval) -> SavedQuestion:
    return SavedQuestion(
        question_id=item.question.question_id,
        question_text=item.question.question_text,
        gold_answer=item.question.gold_answer,
        candidate_answer=item.candidate_answer,
        judge_verdict=item.verdict.verdict,
        judge_reasoning=item.verdict.reasoning,
        retrieved_facts=[fact.content for fact in item.query_result.retrieved_facts],
        diff=item.diff,
        diagnosis=item.diagnosis,
    )


def save_last_run(
    *,
    dataset: str,
    source: Path,
    adapter: str,
    items: list[QuestionEval],
) -> Path:
    path = last_run_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = SavedRun(
        created_at=datetime.now(UTC).isoformat(),
        dataset=dataset,
        source=str(source),
        adapter=adapter,
        questions=[record_from_eval(item) for item in items],
    )
    path.write_text(payload.model_dump_json(indent=2), encoding="utf-8")
    return path


def load_last_run() -> SavedRun:
    path = last_run_path()
    if not path.is_file():
        raise MemxError(
            f"No last run found at {path}. Run `memx run ...` first before `memx debug`."
        )
    return SavedRun.model_validate_json(path.read_text(encoding="utf-8"))


def get_saved_question(run: SavedRun, question_id: str) -> SavedQuestion:
    for question in run.questions:
        if question.question_id == question_id:
            return question
    known = ", ".join(q.question_id for q in run.questions) or "(none)"
    raise MemxError(
        f"Question {question_id!r} was not in the last run. Saved ids: {known}"
    )
