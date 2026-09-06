from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import pytest
from typer.testing import CliRunner

from memx.synthesis.prompts import ANSWER_SYSTEM_PROMPT

LOCOMO = Path("tests/test_datasets/fixtures/locomo_sample.json")


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture(autouse=True)
def isolate_last_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "last_run.json"
    monkeypatch.setattr("memx.cli.run_store.last_run_path", lambda: path)
    return path


def completion_payload(verdict: str = "PASS", reasoning: str = "ok", content: str | None = None) -> dict:
    body = content if content is not None else json.dumps({"verdict": verdict, "reasoning": reasoning})
    return {"choices": [{"message": {"content": body}}]}


def mock_judge(monkeypatch: pytest.MonkeyPatch, factory: Callable[..., dict]) -> list[dict]:
    calls: list[dict] = []

    def fake_completion(**kwargs):
        calls.append(kwargs)
        return factory(**kwargs)

    monkeypatch.setattr("memx.judge.litellm_judge.litellm.completion", fake_completion)
    monkeypatch.setattr("memx.synthesis.litellm_answer.litellm.completion", fake_completion)
    return calls


def always_pass(**_kwargs) -> dict:
    return completion_payload("PASS")


def always_fail(**_kwargs) -> dict:
    return completion_payload("FAIL", "wrong")


def pass_relevance_fail_answer(**kwargs) -> dict:
    messages = kwargs.get("messages") or []
    system = messages[0]["content"] if messages else ""
    user = json.loads(messages[1]["content"]) if len(messages) > 1 else {}
    if system == ANSWER_SYSTEM_PROMPT:
        return completion_payload(content="Boston")
    if user.get("gold_answer") == "yes":
        return completion_payload("PASS", "relevant")
    return completion_payload("FAIL", "mismatch")
