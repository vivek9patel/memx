# Adapters

`--adapter` is a built-in short name or an import path `module.path:ClassName`. Implement `export_state` and (for async stores) `wait_until_ready` so diagnostics can snapshot the store; if export/query are inconsistent, Stage 1 and Stage 4 false-positive.

| Name | Class | Extra |
| --- | --- | --- |
| `mem0` | `memx.adapters.mem0:Mem0Adapter` | `pip install "memx-eval[mem0]"` |
| `supermemory` | `memx.adapters.supermemory:SupermemoryAdapter` | `pip install "memx-eval[supermemory]"` |

```bash
pip install "memx-eval[providers]"   # mem0 + supermemory
```

## Mem0

- `MEM0_API_KEY` set: Mem0 platform client.
- Unset: OSS `Memory()` and `OPENAI_API_KEY`. Extraction LLM defaults to `gpt-5-mini`; override with `MEM0_LLM_MODEL`.
- Ingest uses `async_mode` when the SDK accepts it. `wait_until_ready` polls event IDs in parallel.

## SuperMemory

- `SUPERMEMORY_API_KEY` required unless `SUPERMEMORY_BASE_URL` points at a keyless self-host.
- Ingest: `dreaming="instant"`, `custom_id=session_id`, `container_tag=entity_id`.
- `wait_until_ready` polls `documents.get`. Ready when `status=done` and `dreaming_status` is done (or unset). `status=indexing` is still in-progress even if dreaming already finished.
- Query: hybrid search (`search_mode=hybrid`, threshold `0.3`) over memories and chunks.
- `export_state` is `profile()` (static + dynamic). Index-based fact ids mean diffs can look like mass remove/add even when content is similar.
- `reset(entity_id)` calls `documents.delete_bulk` by container tag. `memx run` never calls `reset`.

## Custom adapter

Subclass `BaseMemoryAdapter` and pass the class on the CLI:

```bash
memx run --dataset locomo --adapter mypkg.adapters:MyAdapter --limit 3 --random
```

The class must be constructible with no required arguments (env vars / defaults). Implement `ingest_session`, `query`, `export_state`. Override `wait_until_ready` if ingest returns before the store is queryable. See [python-api.md](python-api.md).

## Ingest scheduling

The harness ingests **every** `BenchmarkCase.sessions` entry in list order, then one `wait_until_ready` for that entity, then asks the selected questions. `--limit` / `--random` only choose which questions to score. Independent cases (`case_id` / LoCoMo `sample_id` / LongMemEval question id) run with `--concurrency`. Sessions inside a case are never parallelized (order matters for knowledge-update).
