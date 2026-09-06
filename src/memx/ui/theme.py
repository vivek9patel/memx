from __future__ import annotations

from rich.theme import Theme

MEMX_THEME = Theme({
    "stage.1": "bold red",
    "stage.2": "bold orange3",
    "stage.3": "bold yellow",
    "stage.4": "bold magenta",
    "stage.none": "bold green",
    "diff.added": "green",
    "diff.removed": "red",
    "diff.status_changed": "cyan",
    "diff.content_changed": "yellow",
    "diff.unchanged": "grey58",
    "pass": "bold green",
    "fail": "bold red",
})
