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

## Built-in datasets

LoCoMo and LongMemEval are registered by default. Official JSON is fetched into `~/.cache/memx/datasets` (override with `MEMX_CACHE_DIR`).

```bash
memx datasets list
memx datasets pull locomo
memx datasets pull longmemeval          # oracle split (evidence sessions only)
# memx datasets pull longmemeval-s      # ~277 MB
# memx datasets pull longmemeval-m      # ~2.7 GB

# Omit --source to use the cache. --limit keeps a first real run cheap;
# add --random to sample across the whole file instead of the first N questions.
memx run --dataset locomo --adapter memx.adapters.mock:MockMemoryAdapter --limit 5 --random
memx run --dataset longmemeval --adapter memx.adapters.mock:MockMemoryAdapter --limit 5 --random --seed 1
```

Pass `--source path/to/file.json` to use a local copy instead of downloading.

## Development

```bash
pytest tests/ -v
```
