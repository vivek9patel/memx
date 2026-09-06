from __future__ import annotations

from rich.console import Console

from memx.ui.progress import build_eval_progress, update_eval_progress
from memx.ui.theme import MEMX_THEME


def test_update_eval_progress_sets_phase() -> None:
    console = Console(theme=MEMX_THEME, force_terminal=True, width=120)
    progress = build_eval_progress(console=console)
    with progress:
        task = progress.add_task("Starting", total=None, status="0 passed / 0 failed")
        update_eval_progress(
            progress,
            task,
            1,
            2,
            phase="Waiting supermemory conv-26 (status=indexing)",
        )
        assert progress.tasks[0].fields["status"]
        assert "Waiting supermemory" in str(progress.tasks[0].description)
        assert "1 passed" in progress.tasks[0].fields["status"]
