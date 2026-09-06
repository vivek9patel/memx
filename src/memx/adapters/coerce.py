from __future__ import annotations

from typing import Any


def as_mapping(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    dump = getattr(value, "model_dump", None)
    if callable(dump):
        payload = dump()
        if isinstance(payload, dict):
            return payload
    raw = getattr(value, "__dict__", None)
    if isinstance(raw, dict):
        return {key: val for key, val in raw.items() if not str(key).startswith("_")}
    return {}


def get_field(value: Any, *names: str, default: Any = None) -> Any:
    for name in names:
        if isinstance(value, dict) and name in value and value[name] is not None:
            return value[name]
        if hasattr(value, name):
            got = getattr(value, name)
            if got is not None:
                return got
    mapping = as_mapping(value)
    for name in names:
        got = mapping.get(name)
        if got is not None:
            return got
    return default


def as_list(payload: Any, *keys: str) -> list[Any]:
    if payload is None:
        return []
    if isinstance(payload, list):
        return payload
    names = keys or ("results", "memories", "documents", "data")
    for name in names:
        found = get_field(payload, name)
        if isinstance(found, list):
            return found
    return []


def text_of(value: Any, *keys: str) -> str:
    if isinstance(value, str):
        return value
    names = keys or ("memory", "content", "text", "chunk", "summary")
    found = get_field(value, *names)
    if found is None:
        return ""
    if isinstance(found, str):
        return found
    return str(found)
