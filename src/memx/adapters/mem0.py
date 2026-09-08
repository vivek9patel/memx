from __future__ import annotations

import json
import os
import threading
import urllib.error
import urllib.request
from collections.abc import Callable
from time import perf_counter
from typing import Any

from memx.adapters.base import BaseMemoryAdapter
from memx.adapters.coerce import as_list, get_field, text_of
from memx.adapters.poll import map_parallel
from memx.exceptions import AdapterError, AdapterTimeoutError
from memx.llm import rejects_custom_temperature
from memx.schemas.query import QueryResult, RetrievedFact
from memx.schemas.session import Session
from memx.schemas.state import EntityState, FactStatus, MemoryFact

_PAGE_SIZE = 100
_DONE = {"succeeded", "success", "completed", "done"}
_FAILED = {"failed", "error"}
_USER_AGENT = "memx/0.1"


def _import_mem0_client(api_key: str | None) -> Any:
    try:
        from mem0 import Memory, MemoryClient
    except ImportError as exc:
        raise AdapterError(
            "Mem0 SDK is not installed. Install the extra: pip install 'memx-eval[mem0]'"
        ) from exc
    if api_key:
        return MemoryClient(api_key=api_key)
    return Memory.from_config({"llm": {"provider": "openai", "config": _oss_llm_config()}})


def _oss_llm_config() -> dict[str, Any]:
    """Mem0 OSS defaults to gpt-5-mini with temperature=0.1, which OpenAI rejects.

    Force the reasoning-model parameter set (no custom temperature) for GPT-5 / o1 / o3.
    Override the extractor with ``MEM0_LLM_MODEL`` or ``OPENAI_MODEL``.
    """
    model = os.environ.get("MEM0_LLM_MODEL") or os.environ.get("OPENAI_MODEL") or "gpt-5-mini"
    config: dict[str, Any] = {"model": model}
    if rejects_custom_temperature(model):
        config["is_reasoning_model"] = True
    return config


class Mem0Adapter(BaseMemoryAdapter):
    """Mem0 platform (`MemoryClient`) or OSS (`Memory`) adapter.

    No-arg construction (CLI): uses ``MEM0_API_KEY`` when set, otherwise OSS
    ``Memory()`` which typically needs ``OPENAI_API_KEY``.

    Platform ingest uses ``async_mode`` when the SDK accepts it, then
    ``wait_until_ready`` polls event IDs in parallel.
    """

    adapter_name: str = "mem0"

    def __init__(
        self,
        client: Any | None = None,
        *,
        api_key: str | None = None,
        event_status_fn: Callable[[str], str] | None = None,
        sleeper: Callable[[float], None] | None = None,
        clock: Callable[[], float] | None = None,
        poll_interval_s: float = 0.5,
    ) -> None:
        import time

        if client is not None:
            self._client = client
        else:
            key = api_key if api_key is not None else os.environ.get("MEM0_API_KEY")
            self._client = _import_mem0_client(key)
        self._api_key = (
            api_key if api_key is not None else os.environ.get("MEM0_API_KEY") or ""
        )
        self._event_status_fn = event_status_fn or self._http_event_status
        self._sleeper = sleeper or time.sleep
        self._clock = clock or time.monotonic
        self._poll_interval_s = poll_interval_s
        self._pending_events: dict[str, list[str]] = {}
        self._lock = threading.Lock()

    def ingest_session(self, session: Session) -> None:
        messages = [
            {"role": turn.speaker.value, "content": turn.content}
            for turn in session.turns
        ]
        metadata = {
            "session_id": session.session_id,
            "dataset_source": session.dataset_source,
        }
        try:
            result = self._add(messages, session.entity_id, session.session_id, metadata)
        except Exception as exc:
            raise AdapterError(f"Mem0 ingest failed for {session.session_id}: {exc}") from exc
        event_ids = _event_ids(result)
        with self._lock:
            pending = self._pending_events.setdefault(session.entity_id, [])
            pending.extend(event_ids)

    def wait_until_ready(
        self,
        entity_id: str,
        timeout_s: float = 30.0,
        on_status: Callable[[str], None] | None = None,
    ) -> None:
        with self._lock:
            pending = list(self._pending_events.get(entity_id, []))
        if not pending:
            return
        deadline = self._clock() + timeout_s
        remaining = pending
        last_seen: dict[str, str] = {}
        while remaining:
            if self._clock() >= deadline:
                detail = ", ".join(
                    f"{event_id} ({last_seen.get(event_id, 'unknown')})" for event_id in remaining
                )
                raise AdapterTimeoutError(
                    f"Mem0 indexing timed out for {entity_id} after {timeout_s:.0f}s ({detail}). "
                    "Increase with --ready-timeout."
                )
            snapshots = map_parallel(self._event_status_fn, remaining)
            last_seen.update({key: str(val).lower() for key, val in snapshots.items()})
            still: list[str] = []
            for event_id in remaining:
                status = last_seen[event_id]
                if status in _FAILED:
                    raise AdapterError(
                        f"Mem0 event {event_id} failed while indexing {entity_id}"
                    )
                if status not in _DONE:
                    still.append(event_id)
            remaining = still
            if remaining:
                _emit_status(
                    on_status,
                    f"Waiting mem0 {entity_id} {len(remaining)} events "
                    f"({last_seen[remaining[0]]})",
                )
                self._sleeper(self._poll_interval_s)
        _emit_status(on_status, f"Ready mem0 {entity_id}")
        with self._lock:
            self._pending_events[entity_id] = []

    def query(self, query_text: str, entity_id: str, top_k: int = 5) -> QueryResult:
        started = perf_counter()
        try:
            payload = self._search(query_text, entity_id, top_k)
        except Exception as exc:
            raise AdapterError(f"Mem0 search failed for {entity_id}: {exc}") from exc
        hits = [
            RetrievedFact(
                fact_id=str(get_field(row, "id", "memory_id") or f"mem0-{index}"),
                content=text_of(row),
                score=_as_float(get_field(row, "score")),
                metadata=dict(get_field(row, "metadata") or {}),
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
        try:
            rows = self._get_all(entity_id)
        except Exception as exc:
            raise AdapterError(f"Mem0 get_all failed for {entity_id}: {exc}") from exc
        facts = [
            MemoryFact(
                fact_id=str(get_field(row, "id", "memory_id") or f"mem0-{index}"),
                entity_id=entity_id,
                content=text_of(row),
                status=FactStatus.ACTIVE,
                metadata=dict(get_field(row, "metadata") or {}),
            )
            for index, row in enumerate(rows)
            if text_of(row).strip()
        ]
        return EntityState(entity_id=entity_id, facts=facts, snapshot_label="current")

    def reset(self, entity_id: str) -> None:
        try:
            self._client.delete_all(user_id=entity_id)
        except Exception as exc:
            raise AdapterError(f"Mem0 delete_all failed for {entity_id}: {exc}") from exc
        with self._lock:
            self._pending_events.pop(entity_id, None)

    def _add(self, messages: list[dict[str, str]], entity_id: str, run_id: str, metadata: dict[str, str]) -> Any:
        attempts = (
            {
                "user_id": entity_id,
                "run_id": run_id,
                "metadata": metadata,
                "async_mode": True,
                "enable_graph": False,
            },
            {"user_id": entity_id, "run_id": run_id, "metadata": metadata, "async_mode": True},
            {"user_id": entity_id, "run_id": run_id, "metadata": metadata},
        )
        return _first_call(self._client.add, messages, attempts)

    def _http_event_status(self, event_id: str) -> str:
        if not self._api_key:
            return "succeeded"
        request = urllib.request.Request(
            f"https://api.mem0.ai/v1/event/{event_id}/",
            headers={
                "Authorization": f"Token {self._api_key}",
                "User-Agent": _USER_AGENT,
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, OSError, ValueError):
            return "unknown"
        return str(get_field(payload, "status") or "unknown")

    def _search(self, query_text: str, entity_id: str, top_k: int) -> Any:
        attempts = (
            {"filters": {"user_id": entity_id}, "top_k": top_k},
            {"filters": {"user_id": entity_id}, "limit": top_k},
            {"user_id": entity_id, "top_k": top_k},
            {"user_id": entity_id, "limit": top_k},
        )
        return _first_call(self._client.search, query_text, attempts)

    def _get_all(self, entity_id: str) -> list[Any]:
        collected: list[Any] = []
        page = 1
        while page <= 100:
            attempts = (
                {"filters": {"user_id": entity_id}, "page": page, "page_size": _PAGE_SIZE},
                {"user_id": entity_id, "page": page, "page_size": _PAGE_SIZE},
                {"filters": {"user_id": entity_id}},
                {"user_id": entity_id},
            )
            payload = _first_call(self._client.get_all, None, attempts)
            rows = as_list(payload)
            collected.extend(rows)
            if len(rows) < _PAGE_SIZE:
                break
            page += 1
        return collected


def _first_call(fn: Any, positional: str | None, attempts: tuple[dict[str, Any], ...]) -> Any:
    last: Exception | None = None
    for kwargs in attempts:
        try:
            if positional is None:
                return fn(**kwargs)
            return fn(positional, **kwargs)
        except (TypeError, ValueError) as exc:
            last = exc
            continue
    if last is not None:
        raise last
    raise AdapterError("Mem0 client call failed with no attempts.")


def _event_ids(payload: Any) -> list[str]:
    rows = as_list(payload)
    if isinstance(payload, dict) and not rows:
        rows = [payload]
    ids: list[str] = []
    for row in rows:
        event_id = get_field(row, "event_id", "eventId")
        if event_id:
            ids.append(str(event_id))
    return ids


def _emit_status(on_status: Callable[[str], None] | None, message: str) -> None:
    if on_status is not None:
        on_status(message)


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
