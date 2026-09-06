from __future__ import annotations

from memx.cli.engine import evaluate_questions
from memx.cli.main import app
from memx.datasets.registry import get_loader
from memx.diagnostics.classifier import DiagnosticClassifier
from memx.diagnostics.snapshot import StateSnapshotEngine
from memx.diagnostics.taxonomy import FailureStage
from memx.judge.litellm_judge import LiteLLMJudge
from tests.test_cli.adapters import ExtractionMissAdapter
from tests.test_cli.conftest import LOCOMO, always_fail, mock_judge


def test_end_to_end_extraction_miss_is_stage_1(runner, monkeypatch) -> None:
    mock_judge(monkeypatch, always_fail)
    result = runner.invoke(
        app,
        [
            "run",
            "--dataset",
            "locomo",
            "--source",
            str(LOCOMO),
            "--adapter",
            "tests.test_cli.adapters:ExtractionMissAdapter",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "Extraction Failure" in result.output
    assert "Stage 1" in result.output

    loader = get_loader("locomo", LOCOMO)
    adapter = ExtractionMissAdapter()
    judge = LiteLLMJudge()
    diagnoses = [
        item.diagnosis
        for item in evaluate_questions(
            cases=iter(loader),
            adapter=adapter,
            judge=judge,
            classifier=DiagnosticClassifier(relevance_fn=judge.relevance_fn),
            snapshot_engine=StateSnapshotEngine(),
            synthesizer=None,
            ready_timeout=30.0,
            limit=None,
        )
        if item.diagnosis is not None
    ]
    assert diagnoses
    assert all(d.stage == FailureStage.STAGE_1_EXTRACTION for d in diagnoses)
