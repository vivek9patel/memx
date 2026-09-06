from __future__ import annotations

from rich.console import Console

from memx.diagnostics.taxonomy import FailureStage
from memx.ui.taxonomy_badge import render_taxonomy_badge
from memx.ui.theme import MEMX_THEME


def _console() -> Console:
    return Console(record=True, width=120, theme=MEMX_THEME)


def test_badge_stage_1_contains_label() -> None:
    console = _console()
    console.print(render_taxonomy_badge(FailureStage.STAGE_1_EXTRACTION))
    text = console.export_text()
    assert "Stage 1" in text
    assert "Extraction Failure" in text


def test_badge_no_failure_omits_stage_prefix() -> None:
    console = _console()
    console.print(render_taxonomy_badge(FailureStage.NO_FAILURE))
    text = console.export_text()
    assert "No Failure" in text
    assert "Stage" not in text
