# Python API

The engine only talks to `BaseMemoryAdapter`. Loaders produce `BenchmarkCase` (`sessions` + `questions`). After a FAIL, `DiagnosticClassifier` (`memx.diagnostics`) maps the state diff and `query` result onto a taxonomy stage.

```python
from memx import Session, Turn, Speaker

# adapter: BaseMemoryAdapter (Mem0Adapter, SupermemoryAdapter, or your subclass)
adapter.ingest_session(session)
adapter.wait_until_ready(session.entity_id)
state = adapter.export_state(session.entity_id)
result = adapter.query("where does alex live?", session.entity_id)
```

## Contract

Lifecycle for a case:

1. `export_state(entity_id)` — pre-ingest snapshot
2. `ingest_session(session)` for every session on the case, in order
3. `wait_until_ready(entity_id, timeout_s=..., on_status=...)`
4. `export_state(entity_id)` — post-ingest snapshot
5. `query(text, entity_id)` for each selected question

Synchronous stores may leave `wait_until_ready` as the default no-op. Async stores must block or poll until query/export are consistent, or Stage 1/4 will false-positive.

`reset(entity_id)` is optional. The CLI does not call it.

Raise `AdapterError` on ingest/query/export failure; `AdapterTimeoutError` when the wait exceeds `timeout_s`.

Public types live under `memx.schemas` (`Session`, `Turn`, `Speaker`, `QueryResult`, `EntityState`, `MemoryFact`) and `memx.diagnostics`.
