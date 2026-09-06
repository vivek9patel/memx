from __future__ import annotations

from rich.text import Text

from memx.diagnostics.taxonomy import FAILURE_STAGE_LABELS, FailureStage

_STYLE_KEY = {
    FailureStage.STAGE_1_EXTRACTION: "stage.1",
    FailureStage.STAGE_2_CONFLICT_RESOLUTION: "stage.2",
    FailureStage.STAGE_3_MUTATION: "stage.3",
    FailureStage.STAGE_4_RETRIEVAL: "stage.4",
    FailureStage.NO_FAILURE: "stage.none",
}


def render_taxonomy_badge(stage: FailureStage) -> Text:
    label = FAILURE_STAGE_LABELS[stage]
    style = _STYLE_KEY[stage]
    prefix = f"[Stage {stage.value}] " if stage != FailureStage.NO_FAILURE else ""
    return Text(f"{prefix}{label}", style=style)
