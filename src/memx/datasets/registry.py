from __future__ import annotations

from pathlib import Path

from memx.datasets.base import BaseDatasetLoader
from memx.datasets.locomo import LocomoLoader
from memx.datasets.longmemeval import LongMemEvalLoader
from memx.exceptions import MemxError

_REGISTRY: dict[str, type[BaseDatasetLoader]] = {
    "locomo": LocomoLoader,
    "longmemeval": LongMemEvalLoader,
}


def get_loader(dataset_name: str, source_path: Path | str) -> BaseDatasetLoader:
    try:
        loader_cls = _REGISTRY[dataset_name.lower()]
    except KeyError:
        raise MemxError(
            f"Unknown dataset '{dataset_name}'. Available: {sorted(_REGISTRY)}"
        ) from None
    return loader_cls(source_path)
