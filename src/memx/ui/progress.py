from __future__ import annotations

from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
)

from memx.ui.theme import MEMX_THEME


def build_eval_progress(console: Console | None = None) -> Progress:
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        TextColumn("{task.fields[status]}"),
        console=console or Console(theme=MEMX_THEME),
    )


def update_eval_progress(
    progress: Progress,
    task_id: TaskID,
    passed: int,
    failed: int,
    *,
    phase: str | None = None,
    completed: int | None = None,
) -> None:
    """Refresh pass/fail counts and, optionally, the live phase (ingest/wait/query)."""
    fields: dict[str, object] = {
        "status": f"[pass]{passed} passed[/pass] / [fail]{failed} failed[/fail]",
    }
    if phase is not None:
        fields["description"] = phase
    if completed is not None:
        progress.update(task_id, completed=completed, **fields)
        return
    progress.update(task_id, **fields)
