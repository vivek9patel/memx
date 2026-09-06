from memx.adapters.mock import MockMemoryAdapter
from memx.exceptions import AdapterTimeoutError


class ExtractionMissAdapter(MockMemoryAdapter):
    """No-arg adapter that drops every extracted fact (Stage 1 fixture)."""

    def __init__(self) -> None:
        super().__init__(simulate_extraction_miss_rate=1.0)


class TimeoutCarolineAdapter(MockMemoryAdapter):
    """Times out only on conv-caroline so other cases can finish."""

    def wait_until_ready(self, entity_id: str, timeout_s: float = 30.0, on_status=None) -> None:
        if entity_id == "conv-caroline":
            raise AdapterTimeoutError(f"timed out for {entity_id}")
