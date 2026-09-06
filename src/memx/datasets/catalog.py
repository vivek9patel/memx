from __future__ import annotations

from dataclasses import dataclass

from memx.exceptions import MemxError


@dataclass(frozen=True)
class DatasetSpec:
    """Built-in benchmark: official download URL plus which loader parses it."""

    name: str
    loader_name: str
    url: str
    filename: str
    description: str
    homepage: str


# Official releases. LongMemEval defaults to the oracle split (evidence sessions
# only, ~small JSON). Use longmemeval-s / longmemeval-m for the full haystacks.
_SPECS: tuple[DatasetSpec, ...] = (
    DatasetSpec(
        name="locomo",
        loader_name="locomo",
        url="https://raw.githubusercontent.com/snap-research/locomo/main/data/locomo10.json",
        filename="locomo10.json",
        description="LoCoMo 10-session conversations (Maharana et al., ACL 2024).",
        homepage="https://github.com/snap-research/locomo",
    ),
    DatasetSpec(
        name="longmemeval",
        loader_name="longmemeval",
        url=(
            "https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned/"
            "resolve/main/longmemeval_oracle.json"
        ),
        filename="longmemeval_oracle.json",
        description=(
            "LongMemEval oracle split: 500 questions with evidence sessions only "
            "(Wu et al.). Alias of longmemeval-oracle."
        ),
        homepage="https://github.com/xiaowu0162/LongMemEval",
    ),
    DatasetSpec(
        name="longmemeval-oracle",
        loader_name="longmemeval",
        url=(
            "https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned/"
            "resolve/main/longmemeval_oracle.json"
        ),
        filename="longmemeval_oracle.json",
        description="Same file as --dataset longmemeval (oracle / evidence-only).",
        homepage="https://github.com/xiaowu0162/LongMemEval",
    ),
    DatasetSpec(
        name="longmemeval-s",
        loader_name="longmemeval",
        url=(
            "https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned/"
            "resolve/main/longmemeval_s_cleaned.json"
        ),
        filename="longmemeval_s_cleaned.json",
        description="LongMemEval_S cleaned: ~40 history sessions per question (~277 MB).",
        homepage="https://github.com/xiaowu0162/LongMemEval",
    ),
    DatasetSpec(
        name="longmemeval-m",
        loader_name="longmemeval",
        url=(
            "https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned/"
            "resolve/main/longmemeval_m_cleaned.json"
        ),
        filename="longmemeval_m_cleaned.json",
        description="LongMemEval_M cleaned: ~500 history sessions per question (~2.7 GB).",
        homepage="https://github.com/xiaowu0162/LongMemEval",
    ),
)

DATASETS: dict[str, DatasetSpec] = {spec.name: spec for spec in _SPECS}


def available_datasets() -> list[str]:
    return sorted(DATASETS)


def get_spec(dataset_name: str) -> DatasetSpec:
    key = dataset_name.lower().strip()
    try:
        return DATASETS[key]
    except KeyError:
        raise MemxError(
            f"Unknown dataset '{dataset_name}'. Available: {available_datasets()}"
        ) from None
