from __future__ import annotations

from rich.panel import Panel
from rich.table import Table

from memx.diagnostics.models import FactDiffEntry, StateDiff


def render_state_diff(diff: StateDiff) -> Panel:
    table = Table(title=f"State Diff — entity: {diff.entity_id}", expand=True)
    table.add_column("Fact ID", style="dim", no_wrap=True)
    table.add_column("Change")
    table.add_column("Before")
    table.add_column("After")

    for entry in diff.entries:
        if entry.change_type == "unchanged":
            continue  # unchanged rows add noise; omit by default
        table.add_row(*_row_for_entry(entry))

    if table.row_count == 0:
        table.add_row("—", "No mutations detected", "—", "—")

    return Panel(
        table,
        title=f"{diff.pre_snapshot_label} → {diff.post_snapshot_label}",
        border_style="blue",
    )


def _row_for_entry(entry: FactDiffEntry) -> tuple[str, str, str, str]:
    style = f"diff.{entry.change_type}"
    before_text = entry.before.content if entry.before else "—"
    before_status = f" ({entry.before.status.value})" if entry.before else ""
    after_text = entry.after.content if entry.after else "—"
    after_status = f" ({entry.after.status.value})" if entry.after else ""
    return (
        entry.fact_id,
        f"[{style}]{entry.change_type}[/{style}]",
        f"{before_text}{before_status}",
        f"{after_text}{after_status}",
    )
