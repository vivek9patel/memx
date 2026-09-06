# CLI

Entry point: `memx` (`memx.cli.main:app`). `memx --help` lists commands.

Typical loop: pull a dataset, run (ingest → query → judge → diagnose FAILs), then inspect one FAIL.

```bash
memx datasets pull locomo
memx run --dataset locomo --adapter mock --limit 5 --random
memx debug <question_id from the summary>
```

`memx run` judges answers **and** classifies FAILs. `memx debug` reads `.memx/last_run.json` and does not call the adapter.

## `memx run`

Ingest sessions (unless `--skip-ingest`), query, judge, diagnose FAILs, write `.memx/last_run.json` under the current working directory.

```bash
memx run --dataset locomo --adapter mock --limit 5 --random
```

![memx run with the mock adapter](../website/public/shots/02-run-mock.png)

Mock often passes every question (no Diagnostic Summary of FAILs). Use a hosted adapter when you need stage counts.

| Option | Default | Behavior |
| --- | --- | --- |
| `--dataset` | required | `locomo`, `longmemeval`, `longmemeval-s`, `longmemeval-m`, or a name used with `--source` |
| `--adapter` | required | `mock`, `mem0`, `supermemory`, or `module.path:ClassName` |
| `--source` | cache file for `--dataset` | Local JSON path; skips download |
| `--judge-model` | `gpt-4o-mini` | LiteLLM model for pass/fail (and Stage 1 relevance on FAIL) |
| `--answer-model` | unset | LiteLLM model to synthesize an answer from retrieved facts. If omitted, the candidate is concatenated retrieval text |
| `--ready-timeout` | `180` | Seconds `wait_until_ready` may block per entity. One conversation timeout skips that case; other cases continue |
| `--limit` | unset | Cap questions evaluated |
| `--random` | off | With `--limit`, sample uniformly from the full dataset. Requires `--limit` |
| `--seed` | random | RNG seed for `--random`. Printed so you can reproduce |
| `--concurrency` | `4` | Independent conversations in parallel. `--limit` without `--random` forces `1` so “first N” is stable |
| `--skip-ingest` | off | No `ingest_session` / `wait_until_ready`. Query whatever is already in the store for those `entity_id`s |

`--skip-ingest` is not resume-from-timeout. Indexing must already be finished on the backend. Use the same `--dataset` / `--limit` / `--random` / `--seed` as the ingest run so the same questions are scored.

Hosted example (ingest/wait progress while the run is still going):

```bash
memx run --dataset locomo --adapter supermemory --limit 20 --random --seed 2925260458 \
  --answer-model gpt-5-mini --judge-model gpt-4o-mini
```

![Hosted ingest in progress](../website/public/shots/03-run-hosted-progress.png)

Re-score without adding documents again:

```bash
memx run --dataset locomo --adapter supermemory --limit 20 --random --seed 2925260458 \
  --skip-ingest --answer-model gpt-5-mini --judge-model gpt-4o-mini
```

![Re-score with --skip-ingest](../website/public/shots/09-skip-ingest.png)

A second run *without* `--skip-ingest` calls `add` / Mem0 ingest again. memx does not call `reset()`.

GPT-5 / o1 / o3 reject a custom `temperature`. Judge and synthesizer omit it for those model names.

## `memx debug`

Reads `.memx/last_run.json` in the current directory. Does not call the adapter.

```bash
memx debug conv-42_q0221
```

Prints question, gold, candidate, judge verdict, retrieved facts, state diff, and taxonomy stage if the question failed. See [Diagnostics](diagnostics.md).

## `memx datasets`

```bash
memx datasets list
memx datasets pull locomo
memx datasets pull longmemeval
memx datasets pull longmemeval-s --force
```

Downloads land in `~/.cache/memx/datasets` (`MEMX_CACHE_DIR` overrides the cache root). See [Datasets](datasets.md).
