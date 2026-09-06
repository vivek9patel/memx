from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from memx.cli.adapter_loader import load_adapter
from memx.cli.engine import QuestionEval, evaluate_questions
from memx.cli.run_store import save_last_run
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
    adapter: Annotated[str, typer.Option(help="module.path:ClassName of a BaseMemoryAdapter.")],
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
        typer.Option(help="Seconds to wait for adapter indexing after each ingest_session()."),
    ] = 30.0,
    limit: Annotated[int | None, typer.Option(help="Cap the number of questions evaluated.")] = None,
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

    results: list[DiagnosticResult] = []
    traces: list[QuestionEval] = []
    passed = failed = 0
    cases_seen = 0

    with build_eval_progress() as progress:
        task = progress.add_task("Evaluating", total=None, status="0 passed / 0 failed")
        for case in loader:
            cases_seen += 1
            remaining = None if limit is None else max(0, limit - (passed + failed))
            if remaining == 0:
                break
            for item in evaluate_questions(
                cases=iter([case]),
                adapter=adapter_instance,
                judge=judge,
                classifier=classifier,
                snapshot_engine=snapshot_engine,
                synthesizer=synthesizer,
                ready_timeout=ready_timeout,
                limit=remaining,
            ):
                traces.append(item)
                if item.verdict.passed:
                    passed += 1
                else:
                    failed += 1
                    if item.diagnosis is not None:
                        results.append(item.diagnosis)
                update_eval_progress(progress, task, passed, failed)

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
