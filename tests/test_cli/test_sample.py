from __future__ import annotations

from memx.cli.sample import sample_question_ids


def test_sample_is_deterministic_for_a_seed() -> None:
    ids = [f"q{i}" for i in range(20)]
    first, seed_a = sample_question_ids(ids, 5, seed=7)
    second, seed_b = sample_question_ids(ids, 5, seed=7)
    assert seed_a == seed_b == 7
    assert first == second
    assert len(first) == 5
    assert set(first).issubset(ids)


def test_sample_differs_across_seeds() -> None:
    ids = [f"q{i}" for i in range(20)]
    a, _ = sample_question_ids(ids, 5, seed=1)
    b, _ = sample_question_ids(ids, 5, seed=2)
    assert a != b


def test_sample_caps_at_population() -> None:
    sampled, _ = sample_question_ids(["a", "b"], 10, seed=0)
    assert set(sampled) == {"a", "b"}
