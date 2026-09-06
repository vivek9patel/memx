from __future__ import annotations

from typing import Any


def rejects_custom_temperature(model: str | None) -> bool:
    """True when the Chat Completions API only allows the model default temperature.

    GPT-5 family, o1, and o3 reject values such as 0.0 / 0.1.
    """
    if not model:
        return False
    base = model.lower().rsplit("/", 1)[-1]
    if base.startswith(("o1", "o3", "gpt-5")):
        return True
    return False


def litellm_kwargs(model: str, *, temperature: float, **extra: Any) -> dict[str, Any]:
    """LiteLLM completion kwargs; omit temperature when the model forbids it."""
    kwargs: dict[str, Any] = {"model": model, **extra}
    if not rejects_custom_temperature(model):
        kwargs["temperature"] = temperature
    return kwargs
