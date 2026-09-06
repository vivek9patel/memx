from __future__ import annotations

from typing import Annotated

import typer
from rich.console import Console
from rich.progress import BarColumn, DownloadColumn, Progress, TransferSpeedColumn
from rich.table import Table

from memx.datasets.catalog import DATASETS, available_datasets, get_spec
from memx.datasets.fetch import cached_path, ensure_dataset
from memx.exceptions import MemxError
from memx.ui.theme import MEMX_THEME

datasets_app = typer.Typer(
    name="datasets",
    help="List and download the built-in LoCoMo and LongMemEval releases.",
    no_args_is_help=True,
)


@datasets_app.command("list")
def list_datasets() -> None:
    """Show built-in datasets and whether they are already cached locally."""
    console = Console(theme=MEMX_THEME)
    table = Table(title="Built-in datasets", show_lines=False)
    table.add_column("Name", style="bold")
    table.add_column("Cached")
    table.add_column("Description")
    for name in available_datasets():
        spec = DATASETS[name]
        dest = cached_path(spec)
        cached = str(dest) if dest.exists() else "—"
        table.add_row(name, cached, spec.description)
    console.print(table)
    console.print(
        "Pull with [bold]memx datasets pull locomo[/bold] "
        "or [bold]memx datasets pull longmemeval[/bold]. "
        "Then [bold]memx run --dataset locomo --adapter …[/bold] "
        "(omit --source to use the cache)."
    )


@datasets_app.command("pull")
def pull(
    dataset: Annotated[
        str,
        typer.Argument(help="Built-in name: locomo, longmemeval, longmemeval-s, longmemeval-m."),
    ],
    force: Annotated[
        bool,
        typer.Option("--force", help="Re-download even if the file is already cached."),
    ] = False,
) -> None:
    """Download an official dataset JSON into the memx cache (~/.cache/memx/datasets)."""
    console = Console(theme=MEMX_THEME)
    try:
        spec = get_spec(dataset)
        dest = cached_path(spec)
        if dest.exists() and dest.stat().st_size > 0 and not force:
            console.print(f"Already cached: {dest}")
            console.print(f"Source: {spec.homepage}")
            return

        console.print(f"Downloading [bold]{spec.name}[/bold] from {spec.url}")
        with Progress(
            "[progress.description]{task.description}",
            BarColumn(),
            DownloadColumn(),
            TransferSpeedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Fetching", total=None)

            def on_progress(received: int, total: int | None) -> None:
                if total is not None:
                    progress.update(task, total=total, completed=received)
                else:
                    progress.update(task, completed=received)

            path = ensure_dataset(dataset, force=True, progress=on_progress)
        console.print(f"Saved {path}")
        console.print(f"Source: {spec.homepage}")
    except MemxError as exc:
        console.print(f"[fail]{exc}[/fail]")
        raise typer.Exit(code=1) from exc
