from __future__ import annotations

from memx.llm import litellm_kwargs, rejects_custom_temperature


def test_gpt5_family_rejects_custom_temperature() -> None:
    assert rejects_custom_temperature("gpt-5-mini")
    assert rejects_custom_temperature("gpt-5.1")
    assert rejects_custom_temperature("openai/gpt-5.1")
    assert rejects_custom_temperature("o3-mini")
    assert not rejects_custom_temperature("gpt-4o-mini")
    assert not rejects_custom_temperature(None)


def test_litellm_kwargs_omit_temperature_for_gpt5() -> None:
    kwargs = litellm_kwargs("gpt-5.1", temperature=0.0, messages=[])
    assert "temperature" not in kwargs
    assert kwargs["model"] == "gpt-5.1"


def test_litellm_kwargs_keep_temperature_for_gpt4() -> None:
    kwargs = litellm_kwargs("gpt-4o-mini", temperature=0.0, messages=[])
    assert kwargs["temperature"] == 0.0
