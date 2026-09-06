from __future__ import annotations

from rich.console import Console

from memx.diagnostics.models import DiagnosticResult, FactDiffEntry, StateDiff
from memx.diagnostics.taxonomy import FailureStage
from memx.ui.report import render_debug_view, render_summary_table
from memx.ui.theme import MEMX_THEME


def test_summary_table_counts_and_percentages() -> None:
    results = [
        DiagnosticResult(question_id="q1", stage=FailureStage.STAGE_1_EXTRACTION, rationale="missing"),
        DiagnosticResult(question_id="q2", stage=FailureStage.STAGE_4_RETRIEVAL, rationale="missed"),
        DiagnosticResult(question_id="q3", stage=FailureStage.NO_FAILURE, rationale="synthesis"),
    ]
    console = Console(record=True, width=120, theme=MEMX_THEME)
    console.print(render_summary_table(results))
    text = console.export_text()
    assert "50.0%" in text
    assert "—" in text
    assert "Extraction Failure" in text
    assert "Retrieval Failure" in text
    assert "No Failure" in text
    # Two failures → each failure stage is 1/2; zeros for unused stages.
    assert text.count("50.0%") == 2
    assert "0.0%" in text


def test_debug_view_includes_qa_and_diagnosis() -> None:
    diff = StateDiff(
        entity_id="e1",
        pre_snapshot_label="pre_session",
        post_snapshot_label="post_session",
        entries=[],
    )
    diagnosis = DiagnosticResult(
        question_id="q1",
        stage=FailureStage.STAGE_1_EXTRACTION,
        rationale="never extracted",
    )
    console = Console(record=True, width=120, theme=MEMX_THEME)
    console.print(
        render_debug_view(
            question_id="q1",
            question_text="Where does Alex live?",
            gold_answer="Seattle",
            candidate_answer="Boston",
            judge_verdict="FAIL",
            judge_reasoning="wrong city",
            retrieved_facts=["Alex lives in Boston."],
            diff=diff,
            diagnosis=diagnosis,
        )
    )
    text = console.export_text()
    assert "Where does Alex live?" in text
    assert "Seattle" in text
    assert "Boston" in text
    assert "wrong city" in text
    assert "Extraction Failure" in text
    assert "No mutations detected" in text
