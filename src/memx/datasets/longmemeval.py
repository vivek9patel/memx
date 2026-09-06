from __future__ import annotations

import logging
from collections.abc import Iterator
from typing import Any

from pydantic import ValidationError

from memx.datasets.base import BaseDatasetLoader
from memx.schemas.benchmark import BenchmarkCase, BenchmarkQuestion, QuestionCategory
from memx.schemas.session import Session, Speaker, Turn

logger = logging.getLogger(__name__)

_TYPE_MAP: dict[str, QuestionCategory] = {
    "single-session-user": QuestionCategory.SINGLE_HOP,
    "single-session-assistant": QuestionCategory.SINGLE_HOP,
    "multi-session": QuestionCategory.MULTI_HOP,
    "temporal-reasoning": QuestionCategory.TEMPORAL,
    "knowledge-update": QuestionCategory.CONTRADICTION,
    "single-session-preference": QuestionCategory.OPEN_DOMAIN,
}

_ROLE_MAP: dict[str, Speaker] = {
    "user": Speaker.USER,
    "assistant": Speaker.ASSISTANT,
    "system": Speaker.SYSTEM,
}


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return "; ".join(str(item) for item in value)
    return str(value)


class LongMemEvalLoader(BaseDatasetLoader):
    """Parse LongMemEval JSON arrays (`haystack_sessions` records) into cases."""

    dataset_name: str = "longmemeval"

    def iter_cases(self) -> Iterator[BenchmarkCase]:
        self._skipped_count = 0
        for index, record in enumerate(self._iter_raw_records()):
            case = self._parse_record(record, index)
            if case is not None:
                yield case

    def _parse_record(self, record: Any, index: int) -> BenchmarkCase | None:
        record_id = f"index-{index}"
        if not isinstance(record, dict):
            self._skip(record_id, "record is not a JSON object")
            return None

        question_id = _as_text(record.get("question_id")).strip() or record_id
        question_text = _as_text(record.get("question")).strip()
        gold = _as_text(record.get("answer")).strip()
        if not question_text or not gold:
            self._skip(question_id, "empty question text or answer")
            return None

        haystack = record.get("haystack_sessions")
        if not isinstance(haystack, list) or not haystack:
            self._skip(question_id, "missing or empty 'haystack_sessions'")
            return None

        session_ids_raw = record.get("haystack_session_ids")
        dates_raw = record.get("haystack_dates")
        if not isinstance(session_ids_raw, list):
            session_ids_raw = []
        if not isinstance(dates_raw, list):
            dates_raw = []

        try:
            sessions, evidence_turn_ids = self._parse_sessions(
                question_id,
                haystack,
                session_ids_raw,
                dates_raw,
            )
        except ValidationError as exc:
            self._skip(question_id, f"invalid session turns: {exc}")
            return None

        if not sessions:
            self._skip(question_id, "no non-empty sessions")
            return None

        answer_session_ids = record.get("answer_session_ids") or []
        if not isinstance(answer_session_ids, list):
            answer_session_ids = [answer_session_ids]
        known_ids = {session.session_id for session in sessions}
        question_session_id = sessions[0].session_id
        for sid in (str(item) for item in answer_session_ids):
            if sid in known_ids:
                question_session_id = sid
                break
        else:
            if evidence_turn_ids:
                for session in sessions:
                    if any(t.turn_id in evidence_turn_ids for t in session.turns):
                        question_session_id = session.session_id
                        break

        category = self._map_question_type(_as_text(record.get("question_type")).strip())
        question = BenchmarkQuestion(
            question_id=question_id,
            entity_id=question_id,
            session_id=question_session_id,
            question_text=question_text,
            gold_answer=gold,
            category=category,
            evidence_turn_ids=evidence_turn_ids,
            metadata={
                "question_type": record.get("question_type"),
                "question_date": record.get("question_date"),
            },
        )
        return BenchmarkCase(
            case_id=question_id,
            entity_id=question_id,
            sessions=sessions,
            questions=[question],
            dataset_source=self.dataset_name,
        )

    def _parse_sessions(
        self,
        question_id: str,
        haystack: list[Any],
        session_ids: list[Any],
        dates: list[Any],
    ) -> tuple[list[Session], list[str]]:
        sessions: list[Session] = []
        evidence_turn_ids: list[str] = []
        for i, raw_session in enumerate(haystack):
            if not isinstance(raw_session, list):
                continue
            session_id = (
                str(session_ids[i]).strip()
                if i < len(session_ids) and str(session_ids[i]).strip()
                else f"{question_id}_session_{i}"
            )
            turns: list[Turn] = []
            for j, raw_turn in enumerate(raw_session):
                if not isinstance(raw_turn, dict):
                    continue
                content = _as_text(raw_turn.get("content")).strip()
                if not content:
                    continue
                role = _as_text(raw_turn.get("role")).strip().lower() or "user"
                turn_id = f"{session_id}_{j}"
                turns.append(
                    Turn(
                        turn_id=turn_id,
                        speaker=_ROLE_MAP.get(role, Speaker.USER),
                        content=content,
                        metadata={
                            "role": role,
                            **{
                                k: v
                                for k, v in raw_turn.items()
                                if k not in {"role", "content"}
                            },
                        },
                    )
                )
                if raw_turn.get("has_answer"):
                    evidence_turn_ids.append(turn_id)
            if not turns:
                continue
            date = str(dates[i]) if i < len(dates) and dates[i] is not None else None
            sessions.append(
                Session(
                    session_id=session_id,
                    entity_id=question_id,
                    turns=turns,
                    dataset_source=self.dataset_name,
                    metadata={**({"date": date} if date else {})},
                )
            )
        return sessions, evidence_turn_ids

    def _map_question_type(self, question_type: str) -> QuestionCategory:
        mapped = _TYPE_MAP.get(question_type)
        if mapped is not None:
            return mapped
        logger.warning(
            "Unmapped LongMemEval question_type %r; defaulting to OPEN_DOMAIN",
            question_type,
        )
        return QuestionCategory.OPEN_DOMAIN
