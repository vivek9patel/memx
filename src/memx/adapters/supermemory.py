from __future__ import annotations

import os
import threading
import time
from time import perf_counter
from typing import Any, Callable

from memx.adapters.base import BaseMemoryAdapter
from memx.adapters.coerce import as_list, get_field, text_of
from memx.adapters.poll import map_parallel
from memx.exceptions import AdapterError, AdapterTimeoutError
from memx.schemas.query import QueryResult, RetrievedFact
from memx.schemas.session import Session
from memx.schemas.state import EntityState, FactStatus, MemoryFact

_DONE = {"done", "completed", "ready", "success"}
_FAILED = {"failed", "error"}
_DEFAULT_POLL_S = 1.5


def _emit_status(on_status: Callable[[str], None] | None, message: str) -> None:
    if on_status is not None:
        on_status(message)


def _import_supermemory_client(api_key: str | None, base_url: str | None) -> Any:
    try:
        from supermemory import Supermemory
    except ImportError as exc:
        raise AdapterError(
            "Supermemory SDK is not installed. Install the extra: "
            "pip install 'memx-eval[supermemory]'"
        ) from exc
    kwargs: dict[str, Any] = {}
    if api_key:
        kwargs["api_key"] = api_key
    if base_url:
        kwargs["base_url"] = base_url
    return Supermemory(**kwargs)


class SupermemoryAdapter(BaseMemoryAdapter):
    """Supermemory Cloud/self-hosted adapter.

    No-arg construction (CLI): reads ``SUPERMEMORY_API_KEY`` and optional
    ``SUPERMEMORY_BASE_URL``. Ingest uses ``dreaming="instant"`` so
    ``wait_until_ready`` polls those documents in parallel. Query uses
    SuperMemory hybrid search (extracted memories + document chunks).
    """

    adapter_name: str = "supermemory"

    def __init__(
        self,
        client: Any | None = None,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        sleeper: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
        poll_interval_s: float = _DEFAULT_POLL_S,
    ) -> None:
        if client is not None:
            self._client = client
        else:
            key = api_key if api_key is not None else os.environ.get("SUPERMEMORY_API_KEY")
            url = base_url if base_url is not None else os.environ.get("SUPERMEMORY_BASE_URL")
            if not key and not url:
                raise AdapterError(
                    "SUPERMEMORY_API_KEY is not set. Export it or pass api_key=..."
                )
            self._client = _import_supermemory_client(key, url)
        self._sleeper = sleeper
        self._clock = clock
        self._poll_interval_s = poll_interval_s
        self._pending_docs: dict[str, list[str]] = {}
        self._lock = threading.Lock()

    def ingest_session(self, session: Session) -> None:
        content = "\n".join(
            f"{turn.speaker.value}: {turn.content}" for turn in session.turns
        )
        try:
            result = self._client.add(
                content=content,
                container_tag=session.entity_id,
                custom_id=session.session_id,
                dreaming="instant",
                metadata={
                    "session_id": session.session_id,
                    "dataset_source": session.dataset_source,
                },
            )
        except Exception as exc:
            raise AdapterError(
                f"Supermemory ingest failed for {session.session_id}: {exc}"
            ) from exc
        doc_id = get_field(result, "id", "doc_id")
        if doc_id:
            with self._lock:
                self._pending_docs.setdefault(session.entity_id, []).append(str(doc_id))

    def wait_until_ready(
        self,
        entity_id: str,
        timeout_s: float = 30.0,
        on_status: Callable[[str], None] | None = None,
    ) -> None:
        with self._lock:
            pending = list(self._pending_docs.get(entity_id, []))
        if not pending:
            return
        deadline = self._clock() + timeout_s
        remaining = pending
        last_seen: dict[str, str] = {}
        while remaining:
            if self._clock() >= deadline:
                detail = ", ".join(
                    f"{doc_id} ({last_seen.get(doc_id, 'unknown')})" for doc_id in remaining
                )
                raise AdapterTimeoutError(
                    f"Supermemory indexing timed out for {entity_id} after {timeout_s:.0f}s "
                    f"({detail}). Search is not reliable until status=done and "
                    "dreaming_status=done. Increase with --ready-timeout."
                )
            snapshots = map_parallel(self._document_snapshot, remaining)
            last_seen.update(snapshots)
            still: list[str] = []
            for doc_id in remaining:
                snapshot = snapshots[doc_id]
                if _is_failed(snapshot):
                    raise AdapterError(
                        f"Supermemory document {doc_id} failed while indexing {entity_id} "
                        f"({snapshot})"
                    )
                if not _is_ready(snapshot):
                    still.append(doc_id)
            remaining = still
            if remaining:
                sample_id = remaining[0]
                _emit_status(
                    on_status,
                    f"Waiting supermemory {entity_id} "
                    f"{len(remaining)} docs ({last_seen[sample_id]})",
                )
                self._sleeper(self._poll_interval_s)
        _emit_status(on_status, f"Ready supermemory {entity_id}")
        with self._lock:
            self._pending_docs[entity_id] = []

    def query(self, query_text: str, entity_id: str, top_k: int = 5) -> QueryResult:
        started = perf_counter()
        try:
            payload = self._search(query_text, entity_id, top_k)
        except Exception as exc:
            raise AdapterError(f"Supermemory search failed for {entity_id}: {exc}") from exc
        hits = [
            RetrievedFact(
                fact_id=str(get_field(row, "id", "memory_id", "document_id") or f"sm-{index}"),
                content=text_of(row),
                score=_as_float(get_field(row, "score", "similarity")),
                metadata=_search_hit_metadata(row),
            )
            for index, row in enumerate(as_list(payload))
            if text_of(row).strip()
        ]
        return QueryResult(
            query_text=query_text,
            entity_id=entity_id,
            retrieved_facts=hits[:top_k],
            latency_ms=(perf_counter() - started) * 1000,
        )

    def export_state(self, entity_id: str) -> EntityState:
        facts: list[MemoryFact] = []
        try:
            profile = self._client.profile(container_tag=entity_id)
        except Exception:
            profile = None
        inner = get_field(profile, "profile", default=profile)
        for kind in ("static", "dynamic"):
            entries = get_field(inner, kind) or []
            if isinstance(entries, str):
                entries = [entries]
            if not isinstance(entries, list):
                continue
            for index, entry in enumerate(entries):
                content = text_of(entry).strip()
                if not content:
                    continue
                fact_id = str(get_field(entry, "id") or f"sm-{entity_id}-{kind}-{index}")
                facts.append(
                    MemoryFact(
                        fact_id=fact_id,
                        entity_id=entity_id,
                        content=content,
                        status=FactStatus.ACTIVE,
                        metadata={"source": "profile", "kind": kind},
                    )
                )
        return EntityState(entity_id=entity_id, facts=facts, snapshot_label="current")

    def reset(self, entity_id: str) -> None:
        documents = getattr(self._client, "documents", None)
        delete_bulk = getattr(documents, "delete_bulk", None)
        if not callable(delete_bulk):
            raise AdapterError("Supermemory client does not support documents.delete_bulk")
        try:
            delete_bulk(container_tags=[entity_id])
        except TypeError:
            delete_bulk(container_tag=entity_id)
        except Exception as exc:
            raise AdapterError(
                f"Supermemory delete failed for {entity_id}: {exc}"
            ) from exc
        with self._lock:
            self._pending_docs.pop(entity_id, None)

    def _document_snapshot(self, doc_id: str) -> str:
        documents = getattr(self._client, "documents", None)
        getter = getattr(documents, "get", None)
        if not callable(getter):
            return "status=done dreaming_status=done"
        try:
            doc = getter(doc_id)
        except TypeError:
            doc = getter(id=doc_id)
        status = str(get_field(doc, "status") or "").lower()
        dreaming = str(
            get_field(doc, "dreaming_status", "dreamingStatus") or ""
        ).lower()
        return f"status={status or 'unknown'} dreaming_status={dreaming or 'unknown'}"

    def _search(self, query_text: str, entity_id: str, top_k: int) -> Any:
        search = getattr(self._client, "search", None)
        memories = getattr(search, "memories", None) if search is not None else None
        kwargs_list = (
            {
                "q": query_text,
                "container_tag": entity_id,
                "limit": top_k,
                "search_mode": "hybrid",
                "threshold": 0.3,
                "include": {"summaries": True, "chunks": True},
            },
            {
                "q": query_text,
                "container_tag": entity_id,
                "limit": top_k,
                "search_mode": "hybrid",
            },
            {"q": query_text, "container_tag": entity_id, "limit": top_k},
        )
        if callable(search) and not callable(memories):
            return _first_kwargs(search, kwargs_list)
        if callable(memories):
            return _first_kwargs(memories, kwargs_list)
        if callable(search):
            return _first_kwargs(search, kwargs_list)
        raise AdapterError("Supermemory client has no search.memories or search method")


def _search_hit_metadata(row: Any) -> dict[str, Any]:
    metadata = dict(get_field(row, "metadata") or {})
    if get_field(row, "chunk") and not get_field(row, "memory"):
        metadata.setdefault("source", "chunk")
    elif get_field(row, "memory"):
        metadata.setdefault("source", "memory")
    return metadata


def _parse_snapshot(snapshot: str) -> tuple[str, str]:
    status = "unknown"
    dreaming = "unknown"
    for part in snapshot.split():
        if part.startswith("status="):
            status = part.split("=", 1)[1]
        elif part.startswith("dreaming_status="):
            dreaming = part.split("=", 1)[1]
    return status, dreaming


def _is_failed(snapshot: str) -> bool:
    status, dreaming = _parse_snapshot(snapshot)
    return status in _FAILED or dreaming in _FAILED


def _is_ready(snapshot: str) -> bool:
    """Ready when the document is indexed *and* memories are extracted.

    ``dreaming_status=done`` while ``status=indexing`` is not queryable: hybrid
    search returns empty hits and the dashboard still shows indexing. Treat that
    as in-progress, not ready.
    """
    status, dreaming = _parse_snapshot(snapshot)
    if status not in _DONE:
        return False
    return dreaming in _DONE or dreaming in {"", "unknown"}


def _first_kwargs(fn: Any, attempts: tuple[dict[str, Any], ...]) -> Any:
    last: Exception | None = None
    for kwargs in attempts:
        try:
            return fn(**kwargs)
        except TypeError as exc:
            last = exc
            continue
    if last is not None:
        raise last
    raise AdapterError("Supermemory search failed with no attempts.")


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
