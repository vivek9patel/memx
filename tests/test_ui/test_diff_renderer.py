from __future__ import annotations

from rich.console import Console

from memx.diagnostics.models import FactDiffEntry, StateDiff
from memx.schemas.state import MemoryFact
from memx.ui.diff_renderer import render_state_diff
from memx.ui.theme import MEMX_THEME


def _console(*, no_color: bool = False) -> Console:
    return Console(record=True, width=120, theme=MEMX_THEME, no_color=no_color)


def _fact(fact_id: str, content: str) -> MemoryFact:
    return MemoryFact(fact_id=fact_id, entity_id="e1", content=content)


def test_render_state_diff_omits_unchanged_rows() -> None:
    added = _fact("fact-added", "Alex lives in Boston.")
    kept = _fact("fact-kept", "Alex likes tea.")
    diff = StateDiff(
        entity_id="e1",
        pre_snapshot_label="pre_session",
        post_snapshot_label="post_session",
        entries=[
            FactDiffEntry(fact_id="fact-added", change_type="added", after=added),
            FactDiffEntry(fact_id="fact-kept", change_type="unchanged", before=kept, after=kept),
        ],
    )
    console = _console()
    console.print(render_state_diff(diff))
    text = console.export_text()
    assert "fact-added" in text
    assert "fact-kept" not in text


def test_render_state_diff_empty_shows_no_mutations() -> None:
    diff = StateDiff(
        entity_id="e1",
        pre_snapshot_label="pre_session",
        post_snapshot_label="post_session",
        entries=[],
    )
    console = _console()
    console.print(render_state_diff(diff))
    assert "No mutations detected" in console.export_text()


def test_render_state_diff_no_color_is_stable_text() -> None:
    added = _fact("fact-added", "Alex lives in Boston.")
    diff = StateDiff(
        entity_id="e1",
        pre_snapshot_label="pre_session",
        post_snapshot_label="post_session",
        entries=[FactDiffEntry(fact_id="fact-added", change_type="added", after=added)],
    )
    colored = _console()
    plain = _console(no_color=True)
    colored.print(render_state_diff(diff))
    plain.print(render_state_diff(diff))
    colored_text = colored.export_text()
    plain_text = plain.export_text()
    assert "fact-added" in colored_text
    assert "fact-added" in plain_text
    assert "added" in plain_text
