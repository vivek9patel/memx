# memx

Vendor-agnostic Python diagnostic harness for agentic memory systems. Adapters implement a small ingest / wait-until-ready / query / export-state contract; the rest of the toolkit (loaders, diagnostics, CLI) consumes those types.

## Install

```bash
pip install -e ".[dev]"
```

Requires Python 3.11+. Licensed under MIT (see `LICENSE`).

## Core types

```python
from memx import Session, Turn, Speaker, MockMemoryAdapter

adapter = MockMemoryAdapter()
adapter.ingest_session(session)
adapter.wait_until_ready(session.entity_id)
state = adapter.export_state(session.entity_id)
result = adapter.query("where does alex live?", session.entity_id)
```

`MockMemoryAdapter` is an in-memory reference backend for tests. **Mem0** and **Supermemory** ship as first-party adapters (`--adapter mem0` / `--adapter supermemory`). Other backends subclass `BaseMemoryAdapter`. Async backends must override `wait_until_ready()`.

## Built-in providers

SDKs are optional extras so a mock-only install stays small.

```bash
pip install -e ".[mem0]"
export MEM0_API_KEY=...          # platform; omit to use OSS Memory() + OPENAI_API_KEY
# OSS fact extraction defaults to gpt-5-mini. GPT-5 rejects temperature=0.1;
# memx marks those models as reasoning so Mem0 omits temperature.
# Optional: MEM0_LLM_MODEL=gpt-4o-mini
memx run --dataset locomo --adapter mem0 --limit 5 --random

pip install -e ".[supermemory]"
export SUPERMEMORY_API_KEY=...   # optional SUPERMEMORY_BASE_URL for self-host
memx run --dataset locomo --adapter supermemory --limit 5 --random
```

`--adapter mock` is the same as `memx.adapters.mock:MockMemoryAdapter`.

Hosted adapters queue ingest (Mem0 `async_mode`, SuperMemory `dreaming=instant`) and poll pending events/documents **in parallel**. Context sessions with no selected questions are added concurrently, then one `wait_until_ready` covers that batch; a session that has questions still waits on its own so diagnostics snapshot that session. Independent conversations run in parallel with `--concurrency` (default 4). Prefix `--limit` without `--random` stays serial so “first N” is stable.

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
memx run --dataset locomo --adapter mock --limit 5 --random
memx run --dataset longmemeval --adapter mock --limit 5 --random --seed 1
```

`--skip-ingest` reuses the backend as-is: no `ingest_session` / `wait_until_ready`. Same `--dataset` / `--limit` / `--random` / `--seed` as the ingest run, plus whatever `--judge-model` / `--answer-model` you want. Indexing must already be done; this is not resume-from-timeout.

```bash
memx run --dataset locomo --adapter supermemory --limit 4 --random --seed 3691545448 \
  --skip-ingest --answer-model gpt-4o --judge-model gpt-4o
```

Pass `--source path/to/file.json` to use a local copy instead of downloading.

## Development

```bash
pytest tests/ -v
```
