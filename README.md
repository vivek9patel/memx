# memx

Vendor-agnostic harness for evaluating memory systems: it scores answers **and** classifies *why* a question failed.

Ingest conversational sessions into a backend (any adapter), ask benchmark questions, judge the answers, then on each FAIL snapshot the store and assign a stage: extraction, conflict resolution, mutation, or retrieval. Inspect one case with `memx debug`.

## What a run gives you

- Pass/fail per question (LLM judge)
- A **Diagnostic Summary** of FAIL counts by stage
- `.memx/last_run.json` (cwd; gitignored) with gold, candidate, retrieval, state diff, and diagnosis
- `memx debug <question_id>` for one record: question, gold, provider answer, retrieved facts, stage badge, state diff

![Diagnostic Summary after a hosted run](website/public/shots/01-summary-table.png)

![memx debug on a FAIL](website/public/shots/04-debug-question.png)

Passes are not classified. If the judge failed but the store and retrieval look correct, the stage is **No Failure** (often answer synthesis, not memory).

## Failure stages

| Stage | Meaning |
| --- | --- |
| 1 Extraction | Needed fact never entered the store |
| 2 Conflict resolution | Two relevant truths both ACTIVE, no `supersedes` link |
| 3 Mutation | Conflict linked, old row still ACTIVE |
| 4 Retrieval | Store looks correct; search missed the fact |

Details: [docs/diagnostics.md](docs/diagnostics.md).

## Install

Python 3.11+. From this repo:

```bash
pip install -e ".[dev]"
```

Optional backends: `pip install -e ".[mem0]"` or `".[supermemory]"` (or `".[providers]"` for both).

## Quick start

```bash
export SUPERMEMORY_API_KEY=...   # or MEM0_API_KEY and --adapter mem0
memx datasets pull locomo
memx run --dataset locomo --adapter supermemory --limit 5 --random
memx debug <question_id from the summary>
```

See [docs/adapters.md](docs/adapters.md).

Docs: [docs/README.md](docs/README.md). Local site:

```bash
cd website && npm install && npm run dev
```

http://localhost:3000. `npm run build` writes `website/out/` (set the host project root to `website/`; the build still reads `../docs`).

```bash
pytest tests/ -v
```

MIT. See `LICENSE`.
