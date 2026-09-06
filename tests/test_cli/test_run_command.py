from __future__ import annotations

from memx.cli.main import app
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
