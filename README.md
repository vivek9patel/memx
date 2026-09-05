# memx

Vendor-agnostic Python diagnostic harness for agentic memory systems. Adapters implement a small ingest / wait-until-ready / query / export-state contract; the rest of the toolkit (loaders, diagnostics, CLI) consumes those types.

## Install

```bash
pip install -e ".[dev]"
```

Requires Python 3.11+.

## Core types

```python
from memx import Session, Turn, Speaker, MockMemoryAdapter

adapter = MockMemoryAdapter()
adapter.ingest_session(session)
adapter.wait_until_ready(session.entity_id)
state = adapter.export_state(session.entity_id)
result = adapter.query("where does alex live?", session.entity_id)
```

`MockMemoryAdapter` is an in-memory reference backend for tests. Real backends (Mem0, Graphiti, custom stores) subclass `BaseMemoryAdapter`. Async backends must override `wait_until_ready()`.

## Development

```bash
pytest tests/ -v
```
