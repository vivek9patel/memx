from __future__ import annotations

import pytest

from memx.schemas.session import Session, Speaker, Turn


@pytest.fixture
def fixture_session() -> Session:
    """Fixed three-turn session: two user facts plus one assistant ack."""
    return Session(
        session_id="sess-1",
        entity_id="entity-alex",
        dataset_source="synthetic",
        turns=[
            Turn(turn_id="t1", speaker=Speaker.USER, content="Alex lives in Boston."),
            Turn(turn_id="t2", speaker=Speaker.ASSISTANT, content="Got it, Boston."),
            Turn(turn_id="t3", speaker=Speaker.USER, content="Alex works at Acme Corp."),
        ],
    )
