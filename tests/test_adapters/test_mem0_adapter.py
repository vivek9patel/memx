from __future__ import annotations

from memx.adapters.mem0 import Mem0Adapter
from memx.exceptions import AdapterError
from memx.schemas.session import Session


class FakeMem0:
    def __init__(self) -> None:
        self.add_calls: list[dict] = []
        self.store: list[dict] = []

    def add(self, messages, **kwargs):  # noqa: ANN001
        self.add_calls.append({"messages": messages, **kwargs})
        user_id = kwargs["user_id"]
        for message in messages:
            self.store.append(
                {
                    "id": f"m{len(self.store)}",
                    "memory": message["content"],
                    "user_id": user_id,
                    "score": 0.9,
                    "metadata": kwargs.get("metadata") or {},
                }
            )
        return {"results": self.store[-len(messages) :]}

    def search(self, query, **kwargs):  # noqa: ANN001
        needle = query.lower()
        hits = [row for row in self.store if needle in row["memory"].lower()]
        return {"results": hits}

    def get_all(self, **kwargs):
        return {"results": list(self.store)}

    def delete_all(self, **kwargs):
        self.store.clear()


def test_mem0_ingest_query_export_reset(fixture_session: Session) -> None:
    client = FakeMem0()
    adapter = Mem0Adapter(client=client)
    adapter.ingest_session(fixture_session)
    assert client.add_calls[0]["user_id"] == fixture_session.entity_id
    assert client.add_calls[0]["run_id"] == fixture_session.session_id
    assert [m["role"] for m in client.add_calls[0]["messages"]] == [
        "user",
        "assistant",
        "user",
    ]

    state = adapter.export_state(fixture_session.entity_id)
    assert len(state.facts) == 3
    assert any("Boston" in fact.content for fact in state.facts)

    result = adapter.query("Boston", fixture_session.entity_id)
    assert result.retrieved_facts
    assert "Boston" in result.retrieved_facts[0].content

    adapter.reset(fixture_session.entity_id)
    assert adapter.export_state(fixture_session.entity_id).facts == []


def test_mem0_wait_polls_events_in_parallel(fixture_session: Session) -> None:
    statuses = {"e1": "PENDING", "e2": "PENDING"}

    def status_fn(event_id: str) -> str:
        current = statuses[event_id]
        statuses[event_id] = "SUCCEEDED"
        return current

    class EventMem0(FakeMem0):
        def add(self, messages, **kwargs):  # noqa: ANN001
            super().add(messages, **kwargs)
            return [{"event_id": "e1"}, {"event_id": "e2"}]

    ticks = {"n": 0.0}
    adapter = Mem0Adapter(
        client=EventMem0(),
        event_status_fn=status_fn,
        sleeper=lambda s: ticks.__setitem__("n", ticks["n"] + s),
        clock=lambda: ticks["n"],
        poll_interval_s=0.1,
    )
    adapter.ingest_session(fixture_session)
    phases: list[str] = []
    adapter.wait_until_ready(fixture_session.entity_id, timeout_s=5.0, on_status=phases.append)
    assert any("Waiting mem0" in msg for msg in phases)
    assert any("Ready mem0" in msg for msg in phases)



def test_mem0_missing_sdk_message(monkeypatch) -> None:
    monkeypatch.delenv("MEM0_API_KEY", raising=False)

    def boom(_api_key):
        raise AdapterError("Mem0 SDK is not installed. Install the extra: pip install 'memx-eval[mem0]'")

    monkeypatch.setattr("memx.adapters.mem0._import_mem0_client", boom)
    try:
        Mem0Adapter()
    except AdapterError as exc:
        assert "memx-eval[mem0]" in str(exc)
    else:
        raise AssertionError("expected AdapterError")


def test_oss_llm_config_marks_gpt5_as_reasoning(monkeypatch) -> None:
    from memx.adapters.mem0 import _oss_llm_config

    monkeypatch.delenv("MEM0_LLM_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    config = _oss_llm_config()
    assert config["model"] == "gpt-5-mini"
    assert config["is_reasoning_model"] is True

    monkeypatch.setenv("MEM0_LLM_MODEL", "gpt-4o-mini")
    classic = _oss_llm_config()
    assert classic == {"model": "gpt-4o-mini"}
