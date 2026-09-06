from __future__ import annotations

from memx.judge.litellm_judge import LiteLLMJudge
from memx.schemas.query import RetrievedFact
from memx.synthesis.litellm_answer import LiteLLMAnswerSynthesizer
from tests.test_cli.conftest import completion_payload


def test_judge_omits_temperature_for_gpt51(monkeypatch) -> None:
    captured: list[dict] = []

    def fake_completion(**kwargs):
        captured.append(kwargs)
        return completion_payload("PASS", "ok")

    monkeypatch.setattr("memx.judge.litellm_judge.litellm.completion", fake_completion)
    LiteLLMJudge(model="gpt-5.1").score("q", "gold", "cand")
    assert captured
    assert "temperature" not in captured[0]


def test_judge_sends_temperature_for_gpt4(monkeypatch) -> None:
    captured: list[dict] = []

    def fake_completion(**kwargs):
        captured.append(kwargs)
        return completion_payload("PASS", "ok")

    monkeypatch.setattr("memx.judge.litellm_judge.litellm.completion", fake_completion)
    LiteLLMJudge(model="gpt-4o-mini").score("q", "gold", "cand")
    assert captured[0]["temperature"] == 0.0


def test_synthesizer_omits_temperature_for_gpt51(monkeypatch) -> None:
    captured: list[dict] = []

    def fake_completion(**kwargs):
        captured.append(kwargs)
        return {"choices": [{"message": {"content": "Boston"}}]}

    monkeypatch.setattr("memx.synthesis.litellm_answer.litellm.completion", fake_completion)
    LiteLLMAnswerSynthesizer(model="gpt-5.1").synthesize(
        "Where?",
        [RetrievedFact(fact_id="f1", content="Alex lives in Boston.")],
    )
    assert captured
    assert "temperature" not in captured[0]
