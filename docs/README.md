# memx

memx is a vendor-agnostic harness for evaluating memory systems: ingest sessions, ask questions, judge answers, and **diagnose each FAIL** into a four-stage taxonomy (extraction / conflict / mutation / retrieval).

```bash
memx datasets pull locomo
memx run --dataset locomo --adapter mock --limit 5 --random
memx debug <question_id>
```

`memx run` writes a Diagnostic Summary and `.memx/last_run.json`. `memx debug` is how you inspect one FAIL (gold, candidate, retrieval, state diff, stage).

![Diagnostic Summary after a hosted run](../website/public/shots/01-summary-table.png)

| Document | Contents |
| --- | --- |
| [Diagnostics](diagnostics.md) | Why FAILs are classified, stages, `debug`, `last_run.json` |
| [CLI](cli.md) | `memx run`, `memx debug`, `memx datasets` |
| [Adapters](adapters.md) | Built-in backends, env vars, custom adapters |
| [Datasets](datasets.md) | Built-in datasets, cache, `--source` |
| [Python API](python-api.md) | Adapter contract and `memx.diagnostics` |

Requires Python 3.11+. License: MIT.
