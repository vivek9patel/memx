from __future__ import annotations

from memx.diagnostics.models import FactDiffEntry, StateDiff
from memx.schemas.state import EntityState, MemoryFact


class StateSnapshotEngine:
    """Structural (not semantic) diff of two EntityState snapshots for the same entity_id."""

    def diff(self, pre: EntityState, post: EntityState) -> StateDiff:
        """Return a new StateDiff. Does not mutate ``pre`` or ``post``."""
        if pre.entity_id != post.entity_id:
            raise ValueError(
                f"Cannot diff snapshots for different entities: {pre.entity_id!r} vs {post.entity_id!r}"
            )
        pre_by_id: dict[str, MemoryFact] = {f.fact_id: f for f in pre.facts}
        post_by_id: dict[str, MemoryFact] = {f.fact_id: f for f in post.facts}
        entries: list[FactDiffEntry] = []

        for fid, post_fact in post_by_id.items():
            pre_fact = pre_by_id.get(fid)
            if pre_fact is None:
                entries.append(FactDiffEntry(fact_id=fid, change_type="added", after=post_fact))
            elif pre_fact.status != post_fact.status:
                entries.append(
                    FactDiffEntry(
                        fact_id=fid,
                        change_type="status_changed",
                        before=pre_fact,
                        after=post_fact,
                    )
                )
            elif pre_fact.content != post_fact.content:
                entries.append(
                    FactDiffEntry(
                        fact_id=fid,
                        change_type="content_changed",
                        before=pre_fact,
                        after=post_fact,
                    )
                )
            else:
                entries.append(
                    FactDiffEntry(
                        fact_id=fid,
                        change_type="unchanged",
                        before=pre_fact,
                        after=post_fact,
                    )
                )

        for fid, pre_fact in pre_by_id.items():
            if fid not in post_by_id:
                entries.append(FactDiffEntry(fact_id=fid, change_type="removed", before=pre_fact))

        return StateDiff(
            entity_id=pre.entity_id,
            pre_snapshot_label=pre.snapshot_label,
            post_snapshot_label=post.snapshot_label,
            entries=entries,
        )
