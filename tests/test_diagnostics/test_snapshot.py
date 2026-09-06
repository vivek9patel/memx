from __future__ import annotations

import pytest

from memx.diagnostics.snapshot import StateSnapshotEngine
from memx.schemas.state import EntityState, MemoryFact


def test_diff_raises_on_entity_mismatch() -> None:
    engine = StateSnapshotEngine()
    pre = EntityState(entity_id="a", facts=[], snapshot_label="pre")
    post = EntityState(entity_id="b", facts=[], snapshot_label="post")
    with pytest.raises(ValueError, match="Cannot diff snapshots"):
        engine.diff(pre, post)


def test_diff_added_and_removed() -> None:
    engine = StateSnapshotEngine()
    kept = MemoryFact(fact_id="keep", entity_id="e", content="same")
    gone = MemoryFact(fact_id="gone", entity_id="e", content="old")
    added = MemoryFact(fact_id="new", entity_id="e", content="fresh")
    pre = EntityState(entity_id="e", facts=[kept, gone], snapshot_label="pre")
    post = EntityState(entity_id="e", facts=[kept, added], snapshot_label="post")
    diff = engine.diff(pre, post)
    by_id = {entry.fact_id: entry.change_type for entry in diff.entries}
    assert by_id["new"] == "added"
    assert by_id["gone"] == "removed"
    assert by_id["keep"] == "unchanged"
    assert diff.added[0].fact_id == "new"
