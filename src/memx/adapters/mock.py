from __future__ import annotations

import hashlib
import re
from time import perf_counter

from memx.adapters.base import BaseMemoryAdapter
from memx.exceptions import AdapterError
from memx.schemas.query import QueryResult, RetrievedFact
from memx.schemas.session import Session, Speaker, Turn
from memx.schemas.state import EntityState, FactStatus, MemoryFact

_TOKEN_RE = re.compile(r"[a-z0-9]{4,}")


def _tokens(text: str) -> set[str]:
    return set(_TOKEN_RE.findall(text.lower()))


class MockMemoryAdapter(BaseMemoryAdapter):
    """In-memory adapter used as a deterministic test double.

    Facts are stored per ``entity_id`` in insertion order. ``export_state``
    returns that order for inspectability, but callers must treat the snapshot
    as an unordered set of facts.

    Each USER turn is extracted as one ``MemoryFact``. SYSTEM and ASSISTANT
    turns are ignored.

    ``wait_until_ready()`` is the inherited no-op: ingest is synchronous.

    Constructor flags exist so later diagnostic tests can force each taxonomy
    stage without a real backend:

    * ``simulate_extraction_miss_rate`` — fraction of extractable turns skipped
      (Stage 1). Misses are chosen deterministically from ``turn_id``.
    * ``simulate_conflict_blindness`` — when True, contradictory facts are both
      left ACTIVE (Stage 2). When False, the older fact is INVALIDATED and the
      new fact records ``supersedes``.
    """

    adapter_name: str = "mock"

    def __init__(
        self,
        *,
        simulate_extraction_miss_rate: float = 0.0,
        simulate_conflict_blindness: bool = False,
    ) -> None:
        if not 0.0 <= simulate_extraction_miss_rate <= 1.0:
            raise ValueError("simulate_extraction_miss_rate must be in [0.0, 1.0]")
        self.simulate_extraction_miss_rate = simulate_extraction_miss_rate
        self.simulate_conflict_blindness = simulate_conflict_blindness
        self._facts: dict[str, list[MemoryFact]] = {}
        self._seq = 0

    def ingest_session(self, session: Session) -> None:
        store = self._facts.setdefault(session.entity_id, [])
        for turn in session.turns:
            if turn.speaker != Speaker.USER:
                continue
            if self._should_miss_extraction(turn):
                continue
            new_fact = self._fact_from_turn(session.entity_id, turn)
            if not self.simulate_conflict_blindness:
                store[:], superseded_id = self._invalidate_conflicts(store, new_fact)
                if superseded_id is not None:
                    new_fact = new_fact.model_copy(update={"supersedes": superseded_id})
            store.append(new_fact)

    def query(self, query_text: str, entity_id: str, top_k: int = 5) -> QueryResult:
        started = perf_counter()
        facts = self._require_entity(entity_id)
        needle = query_text.lower().strip()
        hits: list[RetrievedFact] = []
        if needle:
            for fact in facts:
                if fact.status != FactStatus.ACTIVE:
                    continue
                haystack = fact.content.lower()
                if needle in haystack or any(tok in haystack for tok in _tokens(query_text)):
                    hits.append(
                        RetrievedFact(
                            fact_id=fact.fact_id,
                            content=fact.content,
                            score=1.0,
                            source_turn_id=fact.created_at_turn,
                            metadata=dict(fact.metadata),
                        )
                    )
                    if len(hits) >= top_k:
                        break
        elapsed_ms = (perf_counter() - started) * 1000
        return QueryResult(
            query_text=query_text,
            entity_id=entity_id,
            retrieved_facts=hits,
            latency_ms=elapsed_ms,
        )

    def export_state(self, entity_id: str) -> EntityState:
        """Return stored facts for ``entity_id``.

        Facts are listed in insertion order. Callers must not depend on that
        order; treat the snapshot as an unordered collection.
        """
        facts = self._require_entity(entity_id)
        return EntityState(
            entity_id=entity_id,
            facts=list(facts),
            snapshot_label="current",
        )

    def reset(self, entity_id: str) -> None:
        self._facts.pop(entity_id, None)

    def _require_entity(self, entity_id: str) -> list[MemoryFact]:
        if entity_id not in self._facts:
            raise AdapterError(f"entity_id {entity_id!r} has never been ingested")
        return self._facts[entity_id]

    def _should_miss_extraction(self, turn: Turn) -> bool:
        rate = self.simulate_extraction_miss_rate
        if rate <= 0.0:
            return False
        if rate >= 1.0:
            return True
        digest = hashlib.sha1(turn.turn_id.encode("utf-8")).digest()
        bucket = int.from_bytes(digest[:2], "big") / 65535.0
        return bucket < rate

    def _next_fact_id(self, entity_id: str, content: str) -> str:
        self._seq += 1
        payload = f"{self._seq}:{entity_id}:{content}".encode()
        return hashlib.sha1(payload).hexdigest()[:16]

    def _fact_from_turn(self, entity_id: str, turn: Turn) -> MemoryFact:
        return MemoryFact(
            fact_id=self._next_fact_id(entity_id, turn.content),
            entity_id=entity_id,
            content=turn.content,
            status=FactStatus.ACTIVE,
            created_at_turn=turn.turn_id,
            metadata={"speaker": turn.speaker.value, **dict(turn.metadata)},
        )

    def _invalidate_conflicts(
        self,
        existing: list[MemoryFact],
        incoming: MemoryFact,
    ) -> tuple[list[MemoryFact], str | None]:
        incoming_tokens = _tokens(incoming.content)
        updated: list[MemoryFact] = []
        superseded_id: str | None = None
        for fact in existing:
            if fact.status != FactStatus.ACTIVE:
                updated.append(fact)
                continue
            prior_tokens = _tokens(fact.content)
            union = incoming_tokens | prior_tokens
            if not union:
                updated.append(fact)
                continue
            jaccard = len(incoming_tokens & prior_tokens) / len(union)
            if jaccard >= 0.4:
                superseded_id = fact.fact_id
                updated.append(
                    fact.model_copy(update={"status": FactStatus.INVALIDATED})
                )
            else:
                updated.append(fact)
        return updated, superseded_id
