from __future__ import annotations

import threading
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from memx.cli.adapter_loader import load_adapter
from memx.cli.engine import QuestionEval, evaluate_questions
from memx.cli.run_store import save_last_run
from memx.cli.sample import collect_question_ids, sample_question_ids
from memx.datasets.fetch import ensure_dataset
from memx.datasets.registry import get_loader
from memx.diagnostics.classifier import DiagnosticClassifier
from memx.diagnostics.models import DiagnosticResult
from memx.diagnostics.snapshot import StateSnapshotEngine
from memx.exceptions import AdapterTimeoutError, MemxError
from memx.judge.litellm_judge import LiteLLMJudge
from memx.synthesis.litellm_answer import LiteLLMAnswerSynthesizer
from memx.ui.progress import build_eval_progress, update_eval_progress
from memx.ui.report import print_report
from memx.ui.theme import MEMX_THEME


def run(
    dataset: Annotated[
        str,
        typer.Option(
            help=(
                "Built-in dataset: locomo, longmemeval (oracle), "
                "longmemeval-s, longmemeval-m. Custom JSON still works with --source."
            )
        ),
    ],
    adapter: Annotated[
        str,
        typer.Option(
            help=(
                "Built-in adapter name (mock, mem0, supermemory) or "
                "module.path:ClassName of a BaseMemoryAdapter."
            )
        ),
    ],
    source: Annotated[
        Path | None,
        typer.Option(
            help=(
                "Path to a dataset JSON file. Omit to download/use the official "
                "file from ~/.cache/memx/datasets (see memx datasets list)."
            )
        ),
    ] = None,
    judge_model: Annotated[
        str, typer.Option(help="LiteLLM model string for pass/fail judging.")
    ] = "gpt-4o-mini",
    answer_model: Annotated[
        str | None,
        typer.Option(
            help=(
                "LiteLLM model for answer synthesis from retrieved facts. "
                "Omit for retrieval-only mode (fact concatenation)."
            )
        ),
    ] = None,
    ready_timeout: Annotated[
        float,
        typer.Option(
            help=(
                "Seconds to wait for adapter indexing after each ingest_session(). "
                "LoCoMo sessions on hosted providers often need 120–300s."
            )
        ),
    ] = 180.0,
    limit: Annotated[int | None, typer.Option(help="Cap the number of questions evaluated.")] = None,
    random_sample: Annotated[
        bool,
        typer.Option(
            "--random",
            help=(
                "With --limit, sample that many questions uniformly from the full "
                "dataset instead of taking the first N. Requires --limit."
            ),
        ),
    ] = False,
    seed: Annotated[
        int | None,
        typer.Option(
            help="RNG seed for --random. If omitted, a seed is chosen and printed so you can reproduce the sample."
        ),
    ] = None,
    concurrency: Annotated[
        int,
        typer.Option(
            help=(
                "Independent cases (conversations) to ingest/wait in parallel. "
                "Prefix --limit without --random stays serial so 'first N' is stable."
            )
        ),
    ] = 4,
    skip_ingest: Annotated[
        bool,
        typer.Option(
            "--skip-ingest",
            help=(
                "Do not ingest or wait; query the existing store for these entity_ids. "
                "Use after a prior run that already added sessions. Indexing must already be done."
            ),
        ),
    ] = False,
) -> None:
    """Run a full benchmark: ingest sessions, ask questions, judge answers, diagnose failures."""
    console = Console(theme=MEMX_THEME)
    try:
        _run(
            dataset=dataset,
            source=source,
            adapter=adapter,
            judge_model=judge_model,
            answer_model=answer_model,
            ready_timeout=ready_timeout,
            limit=limit,
            random_sample=random_sample,
            seed=seed,
            concurrency=concurrency,
            skip_ingest=skip_ingest,
            console=console,
        )
    except AdapterTimeoutError as exc:
        console.print(f"[fail]Adapter indexing timed out: {exc}[/fail]")
        raise typer.Exit(code=1) from exc
    except MemxError as exc:
        console.print(f"[fail]{exc}[/fail]")
        raise typer.Exit(code=1) from exc
    except FileNotFoundError as exc:
        console.print(f"[fail]{exc}[/fail]")
        raise typer.Exit(code=1) from exc


def _run(
    *,
    dataset: str,
    source: Path | None,
    adapter: str,
    judge_model: str,
    answer_model: str | None,
    ready_timeout: float,
    limit: int | None,
    random_sample: bool,
    seed: int | None,
    concurrency: int,
    skip_ingest: bool,
    console: Console,
) -> list[DiagnosticResult]:
    resolved = ensure_dataset(dataset, source=source)
    console.print(f"Dataset {dataset}: {resolved}")
    loader = get_loader(dataset, resolved)
    adapter_instance = load_adapter(adapter)
    judge = LiteLLMJudge(model=judge_model)
    synthesizer = LiteLLMAnswerSynthesizer(model=answer_model) if answer_model else None
    snapshot_engine = StateSnapshotEngine()
    classifier = DiagnosticClassifier(relevance_fn=judge.relevance_fn)

    if random_sample and limit is None:
        raise MemxError("--random requires --limit so the sample size is defined.")

    question_filter: set[str] | None = None
    cases_seen = 0
    if random_sample:
        cases_seen, all_ids = collect_question_ids(loader)
        if not all_ids:
            raise MemxError("Dataset has no questions to sample.")
        sampled, used_seed = sample_question_ids(all_ids, limit or 0, seed)
        question_filter = set(sampled)
        console.print(
            f"Random sample: {len(sampled)}/{len(all_ids)} questions (seed={used_seed})"
        )

    if skip_ingest:
        console.print(
            "Skip ingest: querying existing store (no ingest_session / wait_until_ready; "
            "indexing must already be done)."
        )

    results: list[DiagnosticResult] = []
    traces: list[QuestionEval] = []
    passed = failed = 0
    workers = max(1, concurrency)
    if limit is not None and not random_sample:
        workers = 1
    if workers > 1:
        console.print(f"Concurrency: {workers} cases in parallel")

    with build_eval_progress() as progress:
        task = progress.add_task(
            "Starting",
            total=limit,
            status="0 passed / 0 failed",
        )
        progress_lock = threading.Lock()

        def report(phase: str) -> None:
            with progress_lock:
                update_eval_progress(progress, task, passed, failed, phase=phase)

        def consume(item: QuestionEval) -> None:
            nonlocal passed, failed
            with progress_lock:
                traces.append(item)
                if item.verdict.passed:
                    passed += 1
                else:
                    failed += 1
                    if item.diagnosis is not None:
                        results.append(item.diagnosis)
                update_eval_progress(
                    progress, task, passed, failed, completed=passed + failed
                )

        def run_case(case) -> list[QuestionEval]:
            report(f"Case {case.case_id}")
            return list(
                evaluate_questions(
                    cases=iter([case]),
                    adapter=adapter_instance,
                    judge=judge,
                    classifier=classifier,
                    snapshot_engine=snapshot_engine,
                    synthesizer=synthesizer,
                    ready_timeout=ready_timeout,
                    limit=None,
                    question_ids=question_filter,
                    on_status=report,
                    skip_ingest=skip_ingest,
                )
            )

        if workers == 1:
            for case in loader:
                if question_filter is None:
                    cases_seen += 1
                elif not any(q.question_id in question_filter for q in case.questions):
                    continue
                remaining = None if limit is None or random_sample else max(0, limit - (passed + failed))
                if remaining == 0:
                    break
                report(f"Case {case.case_id}")
                for item in evaluate_questions(
                    cases=iter([case]),
                    adapter=adapter_instance,
                    judge=judge,
                    classifier=classifier,
                    snapshot_engine=snapshot_engine,
                    synthesizer=synthesizer,
                    ready_timeout=ready_timeout,
                    limit=remaining,
                    question_ids=question_filter,
                    on_status=report,
                    skip_ingest=skip_ingest,
                ):
                    consume(item)
        else:
            in_flight: set = set()
            with ThreadPoolExecutor(max_workers=workers) as pool:
                for case in loader:
                    if question_filter is None:
                        cases_seen += 1
                    elif not any(q.question_id in question_filter for q in case.questions):
                        continue
                    in_flight.add(pool.submit(run_case, case))
                    if len(in_flight) >= workers:
                        finished, in_flight = wait(in_flight, return_when=FIRST_COMPLETED)
                        for future in finished:
                            for item in future.result():
                                consume(item)
                if in_flight:
                    finished, _pending = wait(in_flight)
                    for future in finished:
                        for item in future.result():
                            consume(item)


    if cases_seen == 0:
        console.print("[fail]Empty dataset: no cases parsed from the source file.[/fail]")
        raise typer.Exit(code=1)
    saved_path = save_last_run(
        dataset=dataset,
        source=resolved,
        adapter=adapter,
        items=traces,
    )
    console.print(f"Saved last run ({len(traces)} questions) to {saved_path}")
    print_report(results, console=console)
    return results
