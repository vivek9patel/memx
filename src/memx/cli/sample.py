from __future__ import annotations

import random
from collections.abc import Iterable

from memx.schemas.benchmark import BenchmarkCase


def collect_question_ids(cases: Iterable[BenchmarkCase]) -> tuple[int, list[str]]:
    """Return (case_count, question_ids in dataset order)."""
    case_count = 0
    ids: list[str] = []
    for case in cases:
        case_count += 1
        ids.extend(question.question_id for question in case.questions)
    return case_count, ids


def sample_question_ids(
    question_ids: list[str],
    k: int,
    seed: int | None,
) -> tuple[list[str], int]:
    """Uniform sample of up to k distinct IDs. Returns (sampled_ids, seed_used)."""
    unique = list(dict.fromkeys(question_ids))
    used_seed = seed if seed is not None else random.SystemRandom().randrange(2**32)
    if k <= 0 or not unique:
        return [], used_seed
    rng = random.Random(used_seed)
    return rng.sample(unique, min(k, len(unique))), used_seed
