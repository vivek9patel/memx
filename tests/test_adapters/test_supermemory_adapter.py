from __future__ import annotations

from memx.adapters.supermemory import SupermemoryAdapter
from memx.exceptions import AdapterError, AdapterTimeoutError
from memx.schemas.session import Session


class FakeDocuments:
    def __init__(self, parent: FakeSupermemory) -> None:
        self._parent = parent

    def get(self, doc_id: str):
        return self._parent.docs[doc_id]

    def delete_bulk(self, **kwargs):
        tag = None
        tags = kwargs.get("container_tags")
        if tags:
            tag = tags[0]
        tag = kwargs.get("container_tag", tag)
        self._parent.docs = {
            key: doc
            for key, doc in self._parent.docs.items()
            if doc.get("container_tag") != tag
        }


class FakeSearch:
    def __init__(self, parent: FakeSupermemory) -> None:
        self._parent = parent

    def memories(self, **kwargs):
        self._parent.search_calls.append(kwargs)
        needle = str(kwargs.get("q", "")).lower()
        hits = []
        for fact in self._parent.profile_facts:
            if needle in fact.lower():
                hits.append({"id": "hit-1", "memory": fact, "score": 0.95})
        for chunk in self._parent.chunks:
            if needle in chunk.lower():
                hits.append({"id": "chunk-1", "chunk": chunk, "score": 0.8})
        return {"results": hits}


class FakeSupermemory:
    def __init__(self) -> None:
        self.docs: dict[str, dict] = {}
        self.add_calls: list[dict] = []
        self.search_calls: list[dict] = []
        self.profile_facts = ["Alex lives in Boston."]
        self.chunks: list[str] = []
        self.documents = FakeDocuments(self)
        self.search = FakeSearch(self)
        self._seq = 0

    def add(self, **kwargs):
        self.add_calls.append(kwargs)
        self._seq += 1
        doc_id = f"doc-{self._seq}"
        self.docs[doc_id] = {
            "id": doc_id,
            "status": "queued",
            "dreaming_status": "dreaming",
            "content": kwargs.get("content"),
            "container_tag": kwargs.get("container_tag"),
        }
        return {"id": doc_id, "status": "queued"}

    def profile(self, container_tag: str):
        return {"profile": {"static": list(self.profile_facts), "dynamic": []}}


def test_supermemory_ingest_wait_query_export(fixture_session: Session) -> None:
    sleeps: list[float] = []
    ticks = {"n": 0.0}
    phases: list[str] = []

    def clock() -> float:
        return ticks["n"]

    def sleeper(seconds: float) -> None:
        sleeps.append(seconds)
        ticks["n"] += seconds
        for doc in client.docs.values():
            doc["status"] = "done"
            doc["dreaming_status"] = "done"

    client = FakeSupermemory()
    adapter = SupermemoryAdapter(
        client=client,
        sleeper=sleeper,
        clock=clock,
        poll_interval_s=0.1,
    )
    adapter.ingest_session(fixture_session)
    assert client.add_calls[0]["container_tag"] == fixture_session.entity_id
    assert client.add_calls[0]["custom_id"] == fixture_session.session_id
    assert client.add_calls[0]["dreaming"] == "instant"
    assert "user: Alex lives in Boston." in client.add_calls[0]["content"]

    adapter.wait_until_ready(
        fixture_session.entity_id,
        timeout_s=5.0,
        on_status=phases.append,
    )
    assert sleeps
    assert any("Waiting supermemory" in msg for msg in phases)
    assert any("Ready supermemory" in msg for msg in phases)

    state = adapter.export_state(fixture_session.entity_id)
    assert any("Boston" in fact.content for fact in state.facts)

    result = adapter.query("Boston", fixture_session.entity_id)
    assert result.retrieved_facts
    assert "Boston" in result.retrieved_facts[0].content
    assert client.search_calls[0]["search_mode"] == "hybrid"


def test_supermemory_hybrid_query_reads_document_chunks(fixture_session: Session) -> None:
    client = FakeSupermemory()
    client.profile_facts = []
    client.chunks = ["Nate shared her book with the writers group in August 2022."]
    adapter = SupermemoryAdapter(client=client, sleeper=lambda _s: None, clock=lambda: 0.0)
    result = adapter.query("writers group", fixture_session.entity_id)
    assert result.retrieved_facts
    assert "her book" in result.retrieved_facts[0].content
    assert result.retrieved_facts[0].metadata.get("source") == "chunk"


def test_supermemory_dreaming_done_is_not_ready_while_indexing(
    fixture_session: Session,
) -> None:
    ticks = {"n": 0.0}

    def clock() -> float:
        return ticks["n"]

    def sleeper(seconds: float) -> None:
        ticks["n"] += 10

    client = FakeSupermemory()
    adapter = SupermemoryAdapter(
        client=client, sleeper=sleeper, clock=clock, poll_interval_s=0.1
    )
    adapter.ingest_session(fixture_session)
    for doc in client.docs.values():
        doc["status"] = "indexing"
        doc["dreaming_status"] = "done"
    try:
        adapter.wait_until_ready(fixture_session.entity_id, timeout_s=1.0)
    except AdapterTimeoutError as exc:
        assert "status=indexing" in str(exc)
        assert "dreaming_status=done" in str(exc)
        return
    raise AssertionError("expected AdapterTimeoutError")


def test_supermemory_indexing_is_not_ready(fixture_session: Session) -> None:
    ticks = {"n": 0.0}

    def clock() -> float:
        return ticks["n"]

    def sleeper(seconds: float) -> None:
        ticks["n"] += 10

    client = FakeSupermemory()
    adapter = SupermemoryAdapter(
        client=client, sleeper=sleeper, clock=clock, poll_interval_s=0.1
    )
    adapter.ingest_session(fixture_session)
    for doc in client.docs.values():
        doc["status"] = "indexing"
        doc["dreaming_status"] = "dreaming"
    try:
        adapter.wait_until_ready(fixture_session.entity_id, timeout_s=1.0)
    except AdapterTimeoutError as exc:
        assert "status=indexing" in str(exc)
        assert "dreaming_status=dreaming" in str(exc)
        return
    raise AssertionError("expected AdapterTimeoutError")


def test_supermemory_timeout(fixture_session: Session) -> None:
    ticks = {"n": 0.0}

    def clock() -> float:
        return ticks["n"]

    def sleeper(seconds: float) -> None:
        ticks["n"] += 10

    client = FakeSupermemory()
    adapter = SupermemoryAdapter(
        client=client, sleeper=sleeper, clock=clock, poll_interval_s=0.1
    )
    adapter.ingest_session(fixture_session)
    try:
        adapter.wait_until_ready(fixture_session.entity_id, timeout_s=1.0)
    except AdapterTimeoutError:
        return
    raise AssertionError("expected AdapterTimeoutError")


def test_supermemory_requires_api_key(monkeypatch) -> None:
    monkeypatch.delenv("SUPERMEMORY_API_KEY", raising=False)
    monkeypatch.delenv("SUPERMEMORY_BASE_URL", raising=False)
    try:
        SupermemoryAdapter()
    except AdapterError as exc:
        assert "SUPERMEMORY_API_KEY" in str(exc)
    else:
        raise AssertionError("expected AdapterError")
