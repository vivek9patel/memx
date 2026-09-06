# Diagnostics

A FAIL score is not an actionable bug. memx maps each failed question onto a memory-pipeline stage using store snapshots (`export_state` before and after the session) plus what `query` returned.

Classification runs only on questions the judge marked FAIL. Passes are not diagnosed.

## What you look at

After `memx run`, the CLI prints a **Diagnostic Summary** (counts and % of FAILs per stage) and writes `.memx/last_run.json` under the current working directory (gitignored).

![Diagnostic Summary after a hosted run](../website/public/shots/01-summary-table.png)

`memx debug <question_id>` pretty-prints one record: question, gold, candidate, judge verdict, retrieved facts, taxonomy stage, and state diff. It does not call the adapter.

```bash
memx debug conv-42_q0221
```

![memx debug on a FAIL](../website/public/shots/04-debug-question.png)

Hosted SuperMemory FAILs often show related chunks in retrieval while `profile()` (export) does not contain a fact the judge treats as gold-relevant:

![SuperMemory FAIL in debug](../website/public/shots/06-debug-supermemory.png)

Same taxonomy on LongMemEval (oracle / evidence sessions):

![LongMemEval FAIL in debug](../website/public/shots/08-debug-longmemeval.png)

The JSON includes question text, gold, candidate, verdict, retrieved fact strings, diff, and diagnosis. A conversation that hits `AdapterTimeoutError` (or other `AdapterError`) is skipped; questions already finished in other conversations are still saved.

## Stages

Evaluated in order. First match wins.

| Stage | Meaning | Structural signal |
| --- | --- | --- |
| 1 Extraction | Needed fact never entered the store | No post-snapshot fact is relevant to gold (`relevance_fn` = judge, once per fact) |
| 2 Conflict | Two truths both ACTIVE | Multiple relevant ACTIVE facts with no `supersedes` link |
| 3 Mutation | Conflict linked, old row not retired | Relevant fact `supersedes` an id that is still ACTIVE |
| 4 Retrieval | Store looks correct, search missed | Relevant ACTIVE facts exist; none of those ids appear in `query` |
| *(none)* | Memory path looks fine | Judge failed but state + retrieval pass the checks (often synthesis) |

## Pipeline per selected question

1. Ingest preceding context sessions (parallel), then the session that owns the question (serial wait).
2. Snapshot `export_state` before and after that session; diff by fact id.
3. `query` the question text.
4. Build a candidate answer (`--answer-model` or concatenated facts).
5. Judge against gold (`--judge-model`).
6. On FAIL, `DiagnosticClassifier` walks the stages above.

`--skip-ingest` skips 1 and uses empty-pre vs current `export_state`. Query errors become empty retrieval.

Stage 1 cost scales with FAIL count × facts in the snapshot. SuperMemory `profile()` can be large; a cheap `--judge-model` (for example `gpt-4o-mini`) matters more than the answer model on FAILs.

SuperMemory Stage 1 is also sensitive to export vs search: hybrid search can return related chunks while `profile()` does not contain a fact the judge treats as gold-relevant.
