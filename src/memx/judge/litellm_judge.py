from __future__ import annotations

import json

import litellm
from pydantic import BaseModel, ValidationError

from memx.exceptions import MemxError
from memx.judge.prompts import JUDGE_SYSTEM_PROMPT
from memx.llm import litellm_kwargs


class JudgeVerdict(BaseModel):
    verdict: str  # "PASS" | "FAIL"
    reasoning: str

    @property
    def passed(self) -> bool:
        return self.verdict.upper() == "PASS"


class LiteLLMJudge:
    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.0) -> None:
        self.model = model
        self.temperature = temperature

    def score(self, question: str, gold_answer: str, candidate_answer: str) -> JudgeVerdict:
        response = litellm.completion(
            **litellm_kwargs(
                self.model,
                temperature=self.temperature,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "question": question,
                                "gold_answer": gold_answer,
                                "candidate_answer": candidate_answer,
                            }
                        ),
                    },
                ],
            ),
        )
        raw = response["choices"][0]["message"]["content"]
        try:
            return JudgeVerdict.model_validate(json.loads(raw))
        except (json.JSONDecodeError, ValidationError, TypeError) as exc:
            raise MemxError(f"Judge returned malformed JSON: {raw!r}") from exc

    def relevance_fn(self, question, fact_content: str) -> bool:
        """Adapter binding DiagnosticClassifier's RelevanceFn to this judge, reusing score()."""
        verdict = self.score(
            question=f"Is the following fact relevant to answering: {question.question_text!r}?",
            gold_answer="yes",
            candidate_answer=fact_content,
        )
        return verdict.passed
