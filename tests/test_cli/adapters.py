from memx.adapters.mock import MockMemoryAdapter


class ExtractionMissAdapter(MockMemoryAdapter):
    """No-arg adapter that drops every extracted fact (Stage 1 fixture)."""

    def __init__(self) -> None:
        super().__init__(simulate_extraction_miss_rate=1.0)
