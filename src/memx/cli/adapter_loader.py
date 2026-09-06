from __future__ import annotations

import importlib

import typer

from memx.adapters.base import BaseMemoryAdapter
from memx.adapters.registry import BUILTIN_ADAPTERS, resolve_adapter_path
from memx.exceptions import AdapterError


def load_adapter(adapter_path: str) -> BaseMemoryAdapter:
    """Load a built-in name (`mem0`) or ``module.path:ClassName``. Instantiates with no arguments."""
    try:
        adapter_path = resolve_adapter_path(adapter_path)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    if adapter_path.count(":") != 1:
        raise typer.BadParameter(
            "Adapter must be a built-in name "
            f"({', '.join(sorted(BUILTIN_ADAPTERS))}) or 'module.path:ClassName' "
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
    except AdapterError as exc:
        raise typer.BadParameter(str(exc)) from exc
    except TypeError as exc:
        raise typer.BadParameter(
            f"Could not instantiate {adapter_path!r} with a no-arg constructor: {exc}"
        ) from exc
    if not isinstance(instance, BaseMemoryAdapter):
        raise typer.BadParameter(f"{adapter_path!r} did not return a BaseMemoryAdapter.")
    return instance
