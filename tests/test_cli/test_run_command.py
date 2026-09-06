from __future__ import annotations

import json

from memx.cli.main import app
from memx.cli.sample import sample_question_ids
from memx.synthesis.prompts import ANSWER_SYSTEM_PROMPT
from tests.test_cli.conftest import LOCOMO, always_pass, mock_judge, pass_relevance_fail_answer


ADAPTER = "memx.adapters.mock:MockMemoryAdapter"


def _run_args(**extra: str) -> list[str]:
    args = ["run", "--dataset", "locomo", "--source", str(LOCOMO), "--adapter", ADAPTER]
    for key, value in extra.items():
        args.extend([f"--{key.replace('_', '-')}", value])
    return args


def test_run_all_pass_has_no_taxonomy(runner, monkeypatch) -> None:
    mock_judge(monkeypatch, always_pass)
    result = runner.invoke(app, _run_args())
    assert result.exit_code == 0, result.output
    assert "All questions passed." in result.output
    assert "Stage" not in result.output


def test_run_mixed_verdicts_shows_stage_badge(runner, monkeypatch) -> None:
    mock_judge(monkeypatch, pass_relevance_fail_answer)
    result = runner.invoke(app, _run_args())
    assert result.exit_code == 0, result.output
    assert "Stage" in result.output


def test_run_unknown_dataset(runner, monkeypatch) -> None:
    mock_judge(monkeypatch, always_pass)
    result = runner.invoke(
        app,
        ["run", "--dataset", "nonexistent", "--source", str(LOCOMO), "--adapter", ADAPTER],
    )
    assert result.exit_code != 0
    assert "Unknown dataset" in result.output


def test_run_with_answer_model_calls_synthesis(runner, monkeypatch) -> None:
    calls = mock_judge(monkeypatch, pass_relevance_fail_answer)
    result = runner.invoke(app, _run_args(answer_model="gpt-4o-mini"))
    assert result.exit_code == 0, result.output
    systems = [c["messages"][0]["content"] for c in calls if c.get("messages")]
    assert ANSWER_SYSTEM_PROMPT in systems


def test_run_without_answer_model_skips_synthesis(runner, monkeypatch) -> None:
    calls = mock_judge(monkeypatch, always_pass)
    result = runner.invoke(app, _run_args())
    assert result.exit_code == 0, result.output
    systems = [c["messages"][0]["content"] for c in calls if c.get("messages")]
    assert ANSWER_SYSTEM_PROMPT not in systems


def test_run_random_requires_limit(runner, monkeypatch) -> None:
    mock_judge(monkeypatch, always_pass)
    result = runner.invoke(app, _run_args() + ["--random"])
    assert result.exit_code != 0
    assert "--random requires --limit" in result.output


def test_run_limit_without_random_takes_first_questions(
    runner, monkeypatch, isolate_last_run
) -> None:
    mock_judge(monkeypatch, always_pass)
    result = runner.invoke(app, _run_args(limit="1"))
    assert result.exit_code == 0, result.output
    payload = json.loads(isolate_last_run.read_text(encoding="utf-8"))
    assert [q["question_id"] for q in payload["questions"]] == ["conv-caroline_q0000"]


def test_run_random_sample_is_reproducible(
    runner, monkeypatch, isolate_last_run
) -> None:
    mock_judge(monkeypatch, always_pass)
    args = _run_args(limit="1") + ["--random", "--seed", "3"]
    first = runner.invoke(app, args)
    assert first.exit_code == 0, first.output
    assert "Random sample: 1/3 questions (seed=3)" in first.output
    ids_first = [
        q["question_id"]
        for q in json.loads(isolate_last_run.read_text(encoding="utf-8"))["questions"]
    ]
    second = runner.invoke(app, args)
    assert second.exit_code == 0, second.output
    ids_second = [
        q["question_id"]
        for q in json.loads(isolate_last_run.read_text(encoding="utf-8"))["questions"]
    ]
    assert ids_first == ids_second
    assert len(ids_first) == 1
    prefix_run = runner.invoke(app, _run_args(limit="1"))
    assert prefix_run.exit_code == 0, prefix_run.output
    prefix_ids = [
        q["question_id"]
        for q in json.loads(isolate_last_run.read_text(encoding="utf-8"))["questions"]
    ]
    assert prefix_ids == ["conv-caroline_q0000"]
    expected, _ = sample_question_ids(
        ["conv-caroline_q0000", "conv-caroline_q0001", "conv-jon_q0000"],
        1,
        seed=3,
    )
    assert ids_first == expected


def test_run_skip_ingest_does_not_require_ingest(runner, monkeypatch, isolate_last_run) -> None:
    mock_judge(monkeypatch, always_pass)
    result = runner.invoke(app, _run_args(limit="1") + ["--skip-ingest"])
    assert result.exit_code == 0, result.output
    assert "Skip ingest: querying existing store" in result.output
    payload = json.loads(isolate_last_run.read_text(encoding="utf-8"))
    assert [q["question_id"] for q in payload["questions"]] == ["conv-caroline_q0000"]


def test_run_help_mentions_skip_ingest(runner) -> None:
    result = runner.invoke(app, ["run", "--help"])
    assert result.exit_code == 0, result.output
    assert "--skip-ingest" in result.output
