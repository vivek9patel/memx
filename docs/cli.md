# CLI

Entry point: `memx` (`memx.cli.main:app`). `memx --help` lists commands.

Typical loop: pull a dataset, run (ingest → query → judge → diagnose FAILs), then inspect a FAIL with `memx debug`.

```bash
export SUPERMEMORY_API_KEY=...
memx datasets pull locomo
memx run --dataset locomo --adapter supermemory --limit 5 --random
```

`memx run` judges answers **and** classifies FAILs. `memx debug` reads `.memx/last_run.json` and does not call the adapter.

## `memx run`

Ingest sessions (unless `--skip-ingest`), query, judge, diagnose FAILs, write `.memx/last_run.json`.

```bash
memx run --dataset locomo --adapter supermemory --limit 5 --random
```

| Option | Default | Behavior |
| --- | --- | --- |
| `--dataset` | required | `locomo`, `longmemeval`, `longmemeval-s`, `longmemeval-m`, or a name used with `--source` |
| `--adapter` | required | `mem0`, `supermemory`, or `module.path:ClassName` |
| `--source` | cache file for `--dataset` | Local JSON path; skips download |
| `--judge-model` | `gpt-4o-mini` | LiteLLM model for pass/fail (and Stage 1 relevance on FAIL) |
| `--answer-model` | unset | LiteLLM model to synthesize an answer from retrieved facts. If omitted, the candidate is concatenated retrieval text |
| `--ready-timeout` | `180` | Seconds `wait_until_ready` may block per case after all of its sessions are ingested. One conversation timeout skips that case; other cases continue |
| `--limit` | unset | Cap questions **scored**. The owning case still ingests its full `sessions` list |
| `--random` | off | With `--limit`, sample uniformly from the full dataset. Requires `--limit`. Does not drop sessions |
| `--seed` | random | RNG seed for `--random`. Printed so you can reproduce |
| `--concurrency` | `4` | Independent cases in parallel. `--limit` without `--random` forces `1` so “first N” questions is stable |
| `--skip-ingest` | off | No `ingest_session` / `wait_until_ready`. Query whatever is already in the store for those `entity_id`s |

`--limit` / `--random` only choose which questions to ask. For each selected question, memx ingests the **entire** `BenchmarkCase.sessions` haystack (full LoCoMo conversation, or LongMemEval haystack / oracle evidence list), waits, then queries.

`--skip-ingest` is not resume-from-timeout. The full case history must already be indexed. Use the same `--dataset` / `--limit` / `--random` / `--seed` as the ingest run so the same questions are scored.

Hosted example:

```bash
memx run --dataset locomo --adapter supermemory --limit 20 --random --seed 2925260458 \
  --answer-model gpt-5-mini --judge-model gpt-4o-mini
```

Re-score without adding documents again:

```bash
memx run --dataset locomo --adapter supermemory --limit 20 --random --seed 2925260458 \
  --skip-ingest --answer-model gpt-5-mini --judge-model gpt-4o-mini
```

A second run *without* `--skip-ingest` calls `add` / Mem0 ingest again. memx does not call `reset()`.

## `memx debug`

Reads `.memx/last_run.json`. Does not call the adapter. Prints question, gold, candidate, judge verdict, retrieved facts, state diff, and taxonomy stage if the question failed. See [Diagnostics](diagnostics.md).

## `memx datasets`

```bash
memx datasets list
memx datasets pull locomo
memx datasets pull longmemeval
memx datasets pull longmemeval-s --force
```

Downloads land in `~/.cache/memx/datasets` (`MEMX_CACHE_DIR` overrides the cache root). See [Datasets](datasets.md).
