from __future__ import annotations

from collections.abc import Callable

from memx.diagnostics.models import DiagnosticResult, FactDiffEntry, StateDiff
from memx.diagnostics.taxonomy import FailureStage
from memx.schemas.benchmark import BenchmarkQuestion
from memx.schemas.query import QueryResult
from memx.schemas.state import FactStatus

# A relevance function decides whether a given fact's content is
# "the gold-relevant fact" for a question — Prompt 5 wires this to an
# LLM judge; tests in this prompt use a deterministic keyword-overlap stub.
RelevanceFn = Callable[[BenchmarkQuestion, str], bool]


class DiagnosticClassifier:
    """Map a *failed* benchmark question plus its state diff onto a taxonomy stage.

    Precondition: an upstream LLM judge has already scored the question as FAILED.
    ``classify()`` does not decide pass/fail; calling it on a passing question is
    undefined and should be avoided by the CLI.
    """

    def __init__(self, relevance_fn: RelevanceFn) -> None:
        self._is_relevant = relevance_fn

    def classify(
        self,
        question: BenchmarkQuestion,
        diff: StateDiff,
        query_result: QueryResult,
    ) -> DiagnosticResult:
        # --- Stage 1: Extraction Failure ---
        # Structural signal: no POST-ingest fact (added, unchanged, or
        # status/content-changed) has content the relevance function accepts
        # as gold-related. The memory store never captured the needed fact.
        relevant_entries = [
            e
            for e in diff.entries
            if e.after is not None and self._is_relevant(question, e.after.content)
        ]
        if not relevant_entries:
            return DiagnosticResult(
                question_id=question.question_id,
                stage=FailureStage.STAGE_1_EXTRACTION,
                rationale=(
                    "No post-ingest fact content is relevant to the gold answer; "
                    "the underlying information was never extracted into the memory store."
                ),
            )

        # --- Stage 2: Conflict Resolution Failure ---
        # Structural signal: two or more relevant facts remain ACTIVE with no
        # supersedes pointer connecting them. The new fact was written, but the
        # contradiction with an earlier fact was never identified.
        active_relevant = [
            e for e in relevant_entries if e.after and e.after.status == FactStatus.ACTIVE
        ]
        if len(active_relevant) > 1 and self._has_unlinked_contradiction(active_relevant):
            return DiagnosticResult(
                question_id=question.question_id,
                stage=FailureStage.STAGE_2_CONFLICT_RESOLUTION,
                rationale=(
                    "Multiple relevant facts are ACTIVE simultaneously with no "
                    "supersedes link between them; the contradiction was never identified."
                ),
                supporting_diff_entries=active_relevant,
            )

        # --- Stage 3: Mutation Failure ---
        # Structural signal: a relevant ACTIVE fact points at an older fact via
        # supersedes, but that older fact is still ACTIVE instead of
        # deprecated/invalidated. The conflict was linked, the old row was not mutated.
        for entry in active_relevant:
            fact = entry.after
            if fact and fact.supersedes:
                superseded = next(
                    (e for e in diff.entries if e.fact_id == fact.supersedes),
                    None,
                )
                if superseded and superseded.after and superseded.after.status == FactStatus.ACTIVE:
                    return DiagnosticResult(
                        question_id=question.question_id,
                        stage=FailureStage.STAGE_3_MUTATION,
                        rationale=(
                            f"Fact {fact.fact_id!r} supersedes {fact.supersedes!r}, but the "
                            "superseded record was never marked deprecated/invalidated."
                        ),
                        supporting_diff_entries=[entry, superseded],
                    )

        # --- Stage 4: Retrieval Failure ---
        # Structural signal: store state looks correct (relevant ACTIVE facts were
        # retrieved as the current set) but the query result did not include those
        # fact IDs — the retriever returned nothing or a stale/unrelated row.
        retrieved_ids = {f.fact_id for f in query_result.retrieved_facts}
        correct_fact_ids = {e.fact_id for e in active_relevant}
        if not correct_fact_ids & retrieved_ids:
            return DiagnosticResult(
                question_id=question.question_id,
                stage=FailureStage.STAGE_4_RETRIEVAL,
                rationale=(
                    "The correct, current fact exists and is properly ACTIVE in the store, "
                    "but the retriever did not return it for this query."
                ),
                supporting_diff_entries=active_relevant,
                retrieved_fact_ids=list(retrieved_ids),
            )

        # Fallback: state and retrieval both look correct by structural diff,
        # yet the judge marked this FAILED — likely a generation-layer issue
        # outside the 4-stage memory taxonomy. Surface honestly, do not force-fit.
        return DiagnosticResult(
            question_id=question.question_id,
            stage=FailureStage.NO_FAILURE,
            rationale=(
                "State diff and retrieval both appear correct; failure likely originates "
                "in answer synthesis, not the memory pipeline. Flagged for manual review."
            ),
            retrieved_fact_ids=list(retrieved_ids),
        )

    @staticmethod
    def _has_unlinked_contradiction(active_relevant: list[FactDiffEntry]) -> bool:
        # Two+ ACTIVE relevant facts with no supersedes chain connecting them at all.
        linked_ids = {
            e.after.supersedes for e in active_relevant if e.after and e.after.supersedes
        }
        entry_ids = {e.fact_id for e in active_relevant}
        return len(entry_ids - linked_ids) == len(entry_ids) and len(active_relevant) > 1
