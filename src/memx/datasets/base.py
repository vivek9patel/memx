from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from memx.exceptions import MemxError
from memx.schemas.benchmark import BenchmarkCase

logger = logging.getLogger(__name__)


class BaseDatasetLoader(ABC):
    dataset_name: str = "base"

    def __init__(self, source_path: Path | str) -> None:
        self.source_path = Path(source_path)
        if not self.source_path.exists():
            raise FileNotFoundError(f"Dataset source not found: {self.source_path}")
        self._skipped_count = 0
        # First-pass materializes via json.load unless ijson is installed
        # (`pip install memx[streaming]`). iter_cases() is still a generator so
        # downstream consumers stay streaming-shaped.
        self._cached_records: list[Any] | None = None
        self._validate_json_source()

    @property
    def skipped_count(self) -> int:
        """Records skipped for malformation during the most recent iteration."""
        return self._skipped_count

    @abstractmethod
    def iter_cases(self) -> Iterator[BenchmarkCase]:
        """Stream-parse the source file and yield one validated BenchmarkCase at a time."""
        raise NotImplementedError

    def __iter__(self) -> Iterator[BenchmarkCase]:
        return self.iter_cases()

    def count(self) -> int:
        """Materializes the full stream to count cases. Use sparingly on large files."""
        return sum(1 for _ in self.iter_cases())

    def _skip(self, record_id: str, reason: str) -> None:
        logger.warning(
            "Skipping %s record %s: %s",
            self.dataset_name,
            record_id,
            reason,
        )
        self._skipped_count += 1

    def _validate_json_source(self) -> None:
        head = self.source_path.read_bytes()[:64].lstrip()
        if not head.startswith(b"["):
            raise MemxError(
                f"Dataset source {self.source_path} is not a JSON array "
                "(expected a top-level list of records)."
            )
        try:
            import ijson
        except ImportError:
            ijson = None

        if ijson is not None:
            try:
                with self.source_path.open("rb") as fh:
                    next(ijson.items(fh, "item"), None)
            except ijson.JSONError as exc:
                raise MemxError(
                    f"Malformed JSON in dataset source {self.source_path}: {exc}"
                ) from exc
            return

        try:
            with self.source_path.open(encoding="utf-8") as fh:
                payload = json.load(fh)
        except json.JSONDecodeError as exc:
            raise MemxError(
                f"Malformed JSON in dataset source {self.source_path}: {exc}"
            ) from exc
        if not isinstance(payload, list):
            raise MemxError(
                f"Dataset source {self.source_path} is not a JSON array."
            )
        self._cached_records = payload

    def _iter_raw_records(self) -> Iterator[Any]:
        if self._cached_records is not None:
            yield from self._cached_records
            return
        try:
            import ijson
        except ImportError:
            ijson = None
        if ijson is not None:
            with self.source_path.open("rb") as fh:
                yield from ijson.items(fh, "item")
            return
        with self.source_path.open(encoding="utf-8") as fh:
            payload = json.load(fh)
        if not isinstance(payload, list):
            raise MemxError(f"Dataset source {self.source_path} is not a JSON array.")
        yield from payload
