from __future__ import annotations

from memx.cli.main import app
from tests.test_cli.conftest import always_fail, mock_judge, pass_relevance_fail_answer

ADAPTER = "tests.test_cli.adapters:ExtractionMissAdapter"
QUESTION_ID = "conv-caroline_q0000"
LOCOMO_RUN = [
    "run",
    "--dataset",
    "locomo",
    "--source",
    "tests/test_datasets/fixtures/locomo_sample.json",
    "--adapter",
    ADAPTER,
]


def test_debug_without_last_run_errors(runner, isolate_last_run) -> None:
    result = runner.invoke(app, ["debug", QUESTION_ID])
    assert result.exit_code == 1
    assert "No last run found" in result.output


def test_debug_reads_last_run_without_replay(runner, monkeypatch) -> None:
    calls = mock_judge(monkeypatch, pass_relevance_fail_answer)
    run_result = runner.invoke(app, LOCOMO_RUN)
    assert run_result.exit_code == 0, run_result.output
    n_after_run = len(calls)

    debug_result = runner.invoke(app, ["debug", QUESTION_ID])
    assert debug_result.exit_code == 0, debug_result.output
    assert len(calls) == n_after_run
    assert "State Diff" in debug_result.output
    assert "Stage" in debug_result.output
    assert "Where does Caroline live?" in debug_result.output
    assert "Boston" in debug_result.output
    assert "asked" in debug_result.output
    assert "expected (gold)" in debug_result.output
    assert "provider answer" in debug_result.output
    assert "FAIL" in debug_result.output


def test_debug_unknown_id_in_last_run(runner, monkeypatch) -> None:
    mock_judge(monkeypatch, always_fail)
    run_result = runner.invoke(app, LOCOMO_RUN)
    assert run_result.exit_code == 0, run_result.output
    result = runner.invoke(app, ["debug", "does-not-exist"])
    assert result.exit_code == 1
    assert "was not in the last run" in result.output
