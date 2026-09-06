# Datasets

Datasets are the inputs to scoring **and** diagnosis. `memx datasets list` / `pull` and `memx run --dataset` share the same catalog.

![memx datasets list](../website/public/shots/07-datasets-list.png)

Cache directory: `~/.cache/memx/datasets` unless `MEMX_CACHE_DIR` is set.

| `--dataset` | File | Notes |
| --- | --- | --- |
| `locomo` | `locomo10.json` | [LoCoMo](https://github.com/snap-research/locomo): 10 conversations, 1986 questions, 272 sessions |
| `longmemeval` | `longmemeval_oracle.json` | Evidence sessions only (~500 questions). Alias: `longmemeval-oracle` |
| `longmemeval-s` | `longmemeval_s_cleaned.json` | ~40 history sessions per question (~277 MB) |
| `longmemeval-m` | `longmemeval_m_cleaned.json` | ~500 history sessions per question (~2.7 GB) |

```bash
memx datasets pull locomo
memx run --dataset locomo --adapter supermemory --limit 5 --random
```

`--source path/to.json` uses a local file and does not download. The loader is still chosen from `--dataset` (`locomo` vs `longmemeval` JSON shapes).

Sampling:

- `--limit N` without `--random`: first N questions in file order, serial ingest.
- `--limit N --random`: uniform sample of N question ids; `--seed` makes it reproducible.
- LongMemEval: each question is its own case (`entity_id` = question id). Oracle only ingests evidence sessions; `-s` / `-m` ingest the full haystack (hosted cost and `--ready-timeout` go up).
