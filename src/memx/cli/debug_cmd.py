from __future__ import annotations

from typing import Annotated

import typer
from rich.console import Console

from memx.cli.run_store import get_saved_question, load_last_run
from memx.exceptions import MemxError
from memx.ui.report import render_debug_view
from memx.ui.theme import MEMX_THEME


def debug(
    question_id: Annotated[
        str,
        typer.Argument(
            help="question_id from the last `memx run` to inspect (no replay)."
        ),
    ],
) -> None:
    """Show Q/A, judge, diagnosis, and state diff for one question from the last run."""
    console = Console(theme=MEMX_THEME)
    try:
        saved = load_last_run()
        record = get_saved_question(saved, question_id)
    except MemxError as exc:
        console.print(f"[fail]{exc}[/fail]")
        raise typer.Exit(code=1) from exc

    console.print(
        render_debug_view(
            question_id=record.question_id,
            question_text=record.question_text,
            gold_answer=record.gold_answer,
            candidate_answer=record.candidate_answer,
            judge_verdict=record.judge_verdict,
            judge_reasoning=record.judge_reasoning,
            retrieved_facts=list(record.retrieved_facts),
            diff=record.diff,
            diagnosis=record.diagnosis,
        )
    )
