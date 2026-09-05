from __future__ import annotations

from abc import ABC, abstractmethod

from memx.schemas.query import QueryResult
from memx.schemas.session import Session
from memx.schemas.state import EntityState


class BaseMemoryAdapter(ABC):
    """
    Vendor-agnostic contract every memory backend (Mem0, Graphiti, FAISS-backed
    stores, custom systems) must implement to be benchmarked by memx.

    Lifecycle expected by the diagnostic engine (Prompt 3) and CLI (Prompt 5):
        1. export_state(entity_id)   -> pre-session snapshot
        2. ingest_session(session)
        3. wait_until_ready(entity_id) -> block until indexing/extraction is queryable
        4. export_state(entity_id)   -> post-session snapshot
        5. query(text, entity_id)    -> per benchmark question

    Adapters with synchronous ingest (in-memory, fully blocking backends) may
    leave wait_until_ready() as the default no-op. Async backends (vector DBs,
    background embedding pipelines) must override it to poll or block until
    the entity's memories are indexed — otherwise the harness may false-positive
    Stage 1/4 failures.
    """

    adapter_name: str = "base"

    @abstractmethod
    def ingest_session(self, session: Session) -> None:
        """Write a full conversational session into the memory backend."""
        raise NotImplementedError

    @abstractmethod
    def query(self, query_text: str, entity_id: str, top_k: int = 5) -> QueryResult:
        """Retrieve facts relevant to a natural-language query for one entity."""
        raise NotImplementedError

    @abstractmethod
    def export_state(self, entity_id: str) -> EntityState:
        """Return a complete, order-independent snapshot of stored facts for entity_id."""
        raise NotImplementedError

    def wait_until_ready(self, entity_id: str, timeout_s: float = 30.0) -> None:
        """
        Block until async indexing/extraction for entity_id is complete and queryable.

        Override when ingest_session() returns before the backend is consistent
        (e.g. vector index lag, background embedding jobs). Default: no-op.

        Raises AdapterTimeoutError if timeout_s expires before ready.
        """
        return None

    def reset(self, entity_id: str) -> None:
        """Optional: clear all state for entity_id. Default is a no-op; override if supported."""
        return None
