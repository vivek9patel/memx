from __future__ import annotations

from pathlib import Path

from memx.datasets.base import BaseDatasetLoader
from memx.datasets.catalog import get_spec
from memx.datasets.locomo import LocomoLoader
from memx.datasets.longmemeval import LongMemEvalLoader

_LOADERS: dict[str, type[BaseDatasetLoader]] = {
    "locomo": LocomoLoader,
    "longmemeval": LongMemEvalLoader,
}


def get_loader(dataset_name: str, source_path: Path | str) -> BaseDatasetLoader:
    spec = get_spec(dataset_name)
    return _LOADERS[spec.loader_name](source_path)
