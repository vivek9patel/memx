from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from memx.datasets.base import BaseDatasetLoader
from memx.exceptions import MemxError
from memx.schemas.benchmark import BenchmarkCase, BenchmarkQuestion, QuestionCategory
from memx.schemas.session import Session, Speaker, Turn

# LoCoMo paper category integers (Maharana et al., ACL 2024).
_CATEGORY_MAP: dict[int, QuestionCategory] = {
    1: QuestionCategory.MULTI_HOP,
    2: QuestionCategory.TEMPORAL,
    3: QuestionCategory.OPEN_DOMAIN,
    4: QuestionCategory.SINGLE_HOP,
    5: QuestionCategory.ADVERSARIAL,
}

_SESSION_KEY_RE = re.compile(r"^session_(\d+)$")


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return "; ".join(str(item) for item in value)
    return str(value)


class LocomoLoader(BaseDatasetLoader):
    """Parse LoCoMo `locomo10.json`-style arrays into `BenchmarkCase`s.

    Each conversation has two named human speakers (`speaker_a`, `speaker_b`).
    By default both map to ``Speaker.USER``. Pass ``speaker_role_map`` to assign
    roles (for example mapping ``speaker_b``'s name to ``Speaker.ASSISTANT``).
    """

    dataset_name: str = "locomo"

    def __init__(
        self,
        source_path: Path | str,
        speaker_role_map: dict[str, Speaker] | None = None,
    ) -> None:
        super().__init__(source_path)
        self._speaker_role_map = speaker_role_map or {}

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

        sample_id = str(record.get("sample_id") or "").strip() or record_id
        conversation = record.get("conversation")
        if not isinstance(conversation, dict):
            self._skip(sample_id, "missing or invalid 'conversation' object")
            return None

        try:
            sessions = self._parse_sessions(sample_id, conversation)
        except ValidationError as exc:
            self._skip(sample_id, f"invalid session turns: {exc}")
            return None

        if not sessions:
            self._skip(sample_id, "no non-empty sessions")
            return None

        try:
            questions = self._parse_questions(sample_id, record.get("qa"), sessions)
        except MemxError:
            raise
        except ValidationError as exc:
            self._skip(sample_id, f"invalid questions: {exc}")
            return None

        return BenchmarkCase(
            case_id=sample_id,
            entity_id=sample_id,
            sessions=sessions,
            questions=questions,
            dataset_source=self.dataset_name,
        )

    def _parse_sessions(self, sample_id: str, conversation: dict[str, Any]) -> list[Session]:
        numbered: list[tuple[int, list[Any], str | None]] = []
        for key, value in conversation.items():
            match = _SESSION_KEY_RE.match(str(key))
            if match is None:
                continue
            if not isinstance(value, list):
                continue
            n = int(match.group(1))
            date_time = conversation.get(f"session_{n}_date_time")
            numbered.append((n, value, str(date_time) if date_time else None))
        numbered.sort(key=lambda item: item[0])

        sessions: list[Session] = []
        for n, raw_turns, date_time in numbered:
            session_id = f"{sample_id}_session_{n}"
            turns = self._parse_turns(session_id, raw_turns)
            if not turns:
                continue
            sessions.append(
                Session(
                    session_id=session_id,
                    entity_id=sample_id,
                    turns=turns,
                    dataset_source=self.dataset_name,
                    metadata={
                        "session_index": n,
                        "speaker_a": conversation.get("speaker_a"),
                        "speaker_b": conversation.get("speaker_b"),
                        **({"date_time": date_time} if date_time else {}),
                    },
                )
            )
        return sessions

    def _parse_turns(self, session_id: str, raw_turns: list[Any]) -> list[Turn]:
        turns: list[Turn] = []
        for i, raw in enumerate(raw_turns):
            if not isinstance(raw, dict):
                continue
            text = _as_text(raw.get("text")).strip()
            if not text:
                continue
            speaker_name = _as_text(raw.get("speaker")).strip() or "unknown"
            dia_id = _as_text(raw.get("dia_id")).strip() or f"{session_id}_{i}"
            turns.append(
                Turn(
                    turn_id=dia_id,
                    speaker=self._role_for(speaker_name),
                    content=text,
                    metadata={
                        "speaker_name": speaker_name,
                        **{
                            k: v
                            for k, v in raw.items()
                            if k not in {"speaker", "text", "dia_id"}
                        },
                    },
                )
            )
        return turns

    def _role_for(self, speaker_name: str) -> Speaker:
        mapped = self._speaker_role_map.get(speaker_name)
        if mapped is not None:
            return mapped
        return Speaker.USER

    def _parse_questions(
        self,
        sample_id: str,
        raw_qa: Any,
        sessions: list[Session],
    ) -> list[BenchmarkQuestion]:
        if not isinstance(raw_qa, list):
            return []
        turn_to_session = {
            turn.turn_id: session.session_id
            for session in sessions
            for turn in session.turns
        }
        fallback_session_id = sessions[-1].session_id
        questions: list[BenchmarkQuestion] = []
        for i, item in enumerate(raw_qa):
            if not isinstance(item, dict):
                continue
            question_text = _as_text(item.get("question")).strip()
            gold = _as_text(item.get("answer") or item.get("adversarial_answer")).strip()
            if not question_text or not gold:
                continue
            category = self._map_category(item.get("category"))
            evidence = item.get("evidence") or []
            if not isinstance(evidence, list):
                evidence = [evidence]
            evidence_ids = [str(e) for e in evidence if str(e).strip()]
            session_id = fallback_session_id
            for evid in evidence_ids:
                if evid in turn_to_session:
                    session_id = turn_to_session[evid]
                    break
            questions.append(
                BenchmarkQuestion(
                    question_id=f"{sample_id}_q{i:04d}",
                    entity_id=sample_id,
                    session_id=session_id,
                    question_text=question_text,
                    gold_answer=gold,
                    category=category,
                    evidence_turn_ids=evidence_ids,
                    metadata={"locomo_category": item.get("category")},
                )
            )
        return questions

    def _map_category(self, raw: Any) -> QuestionCategory:
        try:
            code = int(raw)
        except (TypeError, ValueError):
            raise MemxError(f"Unknown LoCoMo category code: {raw!r}") from None
        try:
            return _CATEGORY_MAP[code]
        except KeyError:
            raise MemxError(f"Unknown LoCoMo category code: {code}") from None
