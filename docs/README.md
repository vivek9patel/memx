# memx

memx is a vendor-agnostic harness for evaluating memory systems: ingest the full case history, ask questions, judge answers, and **diagnose each FAIL** into a four-stage taxonomy (extraction / conflict / mutation / retrieval).

```bash
pip install "memx-eval[providers]"
export SUPERMEMORY_API_KEY=...
memx datasets pull locomo
memx run --dataset locomo --adapter supermemory --limit 5 --random
```

`memx run` writes a Diagnostic Summary and `.memx/last_run.json`. Swap `--adapter` and `--dataset` and you get which questions each backend misses, and **which pipeline stage** failed — not only a leaderboard score. `memx debug` opens one of those misses: gold, candidate, retrieval, and store diff.

![Diagnostic Summary after a hosted run](../website/public/shots/01-summary-table.png)

| Document | Contents |
| --- | --- |
| [Diagnostics](diagnostics.md) | Stages, `debug`, where adapters fail on a benchmark |
| [CLI](cli.md) | `memx run`, `memx debug`, `memx datasets` |
| [Adapters](adapters.md) | Built-in backends, env vars, custom adapters |
| [Datasets](datasets.md) | Built-in datasets, cache, `--source` |
| [Python API](python-api.md) | Adapter contract and `memx.diagnostics` |

Requires Python 3.11+. License: MIT.
