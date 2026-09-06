from __future__ import annotations

from rich.console import Console, Group
from rich.table import Table
from rich.text import Text

from memx.diagnostics.models import DiagnosticResult, StateDiff
from memx.diagnostics.taxonomy import FailureStage
from memx.ui.diff_renderer import render_state_diff
from memx.ui.taxonomy_badge import render_taxonomy_badge
from memx.ui.theme import MEMX_THEME


def render_summary_table(results: list[DiagnosticResult]) -> Table:
    table = Table(title="Diagnostic Summary")
    table.add_column("Stage")
    table.add_column("Count", justify="right")
    table.add_column("% of Failures", justify="right")

    total = len([r for r in results if r.stage != FailureStage.NO_FAILURE]) or 1
    counts: dict[FailureStage, int] = {}
    for r in results:
        counts[r.stage] = counts.get(r.stage, 0) + 1

    for stage in FailureStage:
        count = counts.get(stage, 0)
        if stage == FailureStage.NO_FAILURE and count == 0:
            continue
        pct = f"{(count / total) * 100:.1f}%" if stage != FailureStage.NO_FAILURE else "—"
        table.add_row(render_taxonomy_badge(stage), str(count), pct)
    return table


def render_full_report(results: list[DiagnosticResult]) -> Group:
    return Group(render_summary_table(results))


def render_debug_view(
    *,
    question_id: str,
    question_text: str,
    gold_answer: str,
    candidate_answer: str,
    judge_verdict: str,
    judge_reasoning: str,
    retrieved_facts: list[str],
    diff: StateDiff,
    diagnosis: DiagnosticResult | None,
) -> Group:
    qa = Table(title="Question", expand=True, show_header=False)
    qa.add_column("Field", style="dim", no_wrap=True)
    qa.add_column("Value", overflow="fold")
    qa.add_row("id", question_id)
    qa.add_row("asked", question_text)
    qa.add_row("expected (gold)", gold_answer)
    qa.add_row("provider answer", candidate_answer.strip() or "—")
    retrieved = "\n".join(retrieved_facts) if retrieved_facts else "—"
    qa.add_row("retrieved facts", retrieved)
    qa.add_row("judge", judge_verdict.upper())
    qa.add_row("judge reasoning", judge_reasoning.strip() or "—")

    if diagnosis is None:
        diagnosis_block: object = Text("PASS", style="pass")
    else:
        diagnosis_block = Group(
            render_taxonomy_badge(diagnosis.stage),
            Text(diagnosis.rationale),
        )

    return Group(qa, diagnosis_block, render_state_diff(diff))


def print_report(results: list[DiagnosticResult], console: Console | None = None) -> None:
    out = console or Console(theme=MEMX_THEME)
    if not results:
        out.print("[pass]All questions passed.[/pass]")
        return
    out.print(render_full_report(results))
