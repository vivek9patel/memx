from __future__ import annotations

from memx.schemas.query import QueryResult
from memx.synthesis.litellm_answer import LiteLLMAnswerSynthesizer


def build_candidate_answer(
    question_text: str,
    query_result: QueryResult,
    synthesizer: LiteLLMAnswerSynthesizer | None,
) -> str:
    """Resolve candidate answer with explicit precedence.

    1. query_result.raw_answer  — adapter did full RAG internally
    2. synthesizer.synthesize() — harness-level answer LLM (e2e mode)
    3. fact concatenation       — retrieval-only fallback (debug / no --answer-model)
    """
    if query_result.raw_answer:
        return query_result.raw_answer
    if synthesizer is not None and query_result.retrieved_facts:
        return synthesizer.synthesize(question_text, query_result.retrieved_facts)
    return "; ".join(f.content for f in query_result.retrieved_facts)
