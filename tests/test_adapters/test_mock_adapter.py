from __future__ import annotations

import pytest
from pydantic import ValidationError

from memx import MockMemoryAdapter, Session
from memx.adapters.base import BaseMemoryAdapter
from memx.exceptions import AdapterError
from memx.schemas.session import Speaker, Turn
from memx.schemas.state import FactStatus


def test_session_rejects_empty_turns() -> None:
    with pytest.raises(ValidationError):
        Session(
            session_id="s1",
            entity_id="e1",
            turns=[],
            dataset_source="synthetic",
        )


def test_turn_rejects_whitespace_only_content() -> None:
    with pytest.raises(ValidationError):
        Turn(turn_id="t1", speaker=Speaker.USER, content="   \n")


def test_session_rejects_empty_ids() -> None:
    turn = Turn(turn_id="t1", speaker=Speaker.USER, content="hello")
    with pytest.raises(ValidationError):
        Session(session_id="  ", entity_id="e1", turns=[turn], dataset_source="synthetic")
    with pytest.raises(ValidationError):
        Session(session_id="s1", entity_id="", turns=[turn], dataset_source="synthetic")


def test_ingest_then_export_fact_count_matches_fixture(fixture_session: Session) -> None:
    adapter = MockMemoryAdapter()
    adapter.ingest_session(fixture_session)
    state = adapter.export_state(fixture_session.entity_id)
    extractable = [t for t in fixture_session.turns if t.speaker == Speaker.USER]
    assert len(state.facts) == len(extractable)
    assert all(f.status == FactStatus.ACTIVE for f in state.facts)
    assert [f.created_at_turn for f in state.facts] == [t.turn_id for t in extractable]


def test_query_never_ingested_entity_raises_adapter_error() -> None:
    adapter = MockMemoryAdapter()
    with pytest.raises(AdapterError, match="never been ingested"):
        adapter.query("where does alex live?", "unknown-entity")


def test_export_state_never_ingested_entity_raises_adapter_error() -> None:
    adapter = MockMemoryAdapter()
    with pytest.raises(AdapterError, match="never been ingested"):
        adapter.export_state("unknown-entity")


def test_base_adapter_cannot_be_instantiated() -> None:
    with pytest.raises(TypeError):
        BaseMemoryAdapter()


def test_wait_until_ready_is_noop_for_ingested_entity(fixture_session: Session) -> None:
    adapter = MockMemoryAdapter()
    adapter.ingest_session(fixture_session)
    adapter.wait_until_ready(fixture_session.entity_id)


def test_query_substring_match(fixture_session: Session) -> None:
    adapter = MockMemoryAdapter()
    adapter.ingest_session(fixture_session)
    result = adapter.query("Boston", fixture_session.entity_id)
    assert result.retrieved_facts
    assert any("Boston" in f.content for f in result.retrieved_facts)


def test_extraction_miss_rate_one_skips_all_facts(fixture_session: Session) -> None:
    adapter = MockMemoryAdapter(simulate_extraction_miss_rate=1.0)
    adapter.ingest_session(fixture_session)
    state = adapter.export_state(fixture_session.entity_id)
    assert state.facts == []


def test_conflict_resolution_invalidates_overlapping_fact() -> None:
    session = Session(
        session_id="s-conflict",
        entity_id="entity-alex",
        dataset_source="synthetic",
        turns=[
            Turn(turn_id="t1", speaker=Speaker.USER, content="Alex lives in Boston."),
            Turn(turn_id="t2", speaker=Speaker.USER, content="Alex lives in Seattle."),
        ],
    )
    adapter = MockMemoryAdapter(simulate_conflict_blindness=False)
    adapter.ingest_session(session)
    state = adapter.export_state(session.entity_id)
    assert len(state.facts) == 2
    first, second = state.facts
    assert first.status == FactStatus.INVALIDATED
    assert second.status == FactStatus.ACTIVE
    assert second.supersedes == first.fact_id


def test_conflict_blindness_keeps_both_active() -> None:
    session = Session(
        session_id="s-blind",
        entity_id="entity-alex",
        dataset_source="synthetic",
        turns=[
            Turn(turn_id="t1", speaker=Speaker.USER, content="Alex lives in Boston."),
            Turn(turn_id="t2", speaker=Speaker.USER, content="Alex lives in Seattle."),
        ],
    )
    adapter = MockMemoryAdapter(simulate_conflict_blindness=True)
    adapter.ingest_session(session)
    state = adapter.export_state(session.entity_id)
    assert all(f.status == FactStatus.ACTIVE for f in state.facts)
    assert all(f.supersedes is None for f in state.facts)
