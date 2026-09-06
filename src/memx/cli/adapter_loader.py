from __future__ import annotations

import importlib

import typer

from memx.adapters.base import BaseMemoryAdapter


def load_adapter(adapter_path: str) -> BaseMemoryAdapter:
    """Load a ``module.path:ClassName`` adapter. Instantiates with no arguments."""
    if adapter_path.count(":") != 1:
        raise typer.BadParameter(
            "Adapter must be in 'module.path:ClassName' format "
            f"(got {adapter_path!r})."
        )
    module_path, class_name = adapter_path.split(":")
    if not module_path or not class_name:
        raise typer.BadParameter(
            "Adapter must be in 'module.path:ClassName' format "
            f"(got {adapter_path!r})."
        )
    try:
        module = importlib.import_module(module_path)
    except ImportError as exc:
        raise typer.BadParameter(f"Could not import adapter module {module_path!r}: {exc}") from exc
    try:
        cls = getattr(module, class_name)
    except AttributeError as exc:
        raise typer.BadParameter(
            f"Module {module_path!r} has no attribute {class_name!r}."
        ) from exc
    if not isinstance(cls, type) or not issubclass(cls, BaseMemoryAdapter):
        raise typer.BadParameter(
            f"{adapter_path!r} is not a BaseMemoryAdapter subclass."
        )
    try:
        instance = cls()
    except TypeError as exc:
        raise typer.BadParameter(
            f"Could not instantiate {adapter_path!r} with a no-arg constructor: {exc}"
        ) from exc
    if not isinstance(instance, BaseMemoryAdapter):
        raise typer.BadParameter(f"{adapter_path!r} did not return a BaseMemoryAdapter.")
    return instance
