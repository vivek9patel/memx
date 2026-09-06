from __future__ import annotations

import json

import litellm

from memx.schemas.query import RetrievedFact
from memx.synthesis.prompts import ANSWER_SYSTEM_PROMPT


class LiteLLMAnswerSynthesizer:
    """Turns retrieved facts into a candidate answer via a fixed LLM.

    Used when the adapter returns facts but does not set QueryResult.raw_answer.
    Keeps answer generation consistent across adapters for fair comparison.
    """

    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.0) -> None:
        self.model = model
        self.temperature = temperature

    def synthesize(self, question: str, facts: list[RetrievedFact]) -> str:
        if not facts:
            return ""
        response = litellm.completion(
            model=self.model,
            temperature=self.temperature,
            messages=[
                {"role": "system", "content": ANSWER_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "question": question,
                            "retrieved_facts": [{"content": f.content} for f in facts],
                        }
                    ),
                },
            ],
        )
        return (response["choices"][0]["message"]["content"] or "").strip()
