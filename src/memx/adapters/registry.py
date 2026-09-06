from __future__ import annotations

# Short CLI names -> module.path:ClassName
BUILTIN_ADAPTERS: dict[str, str] = {
    "mem0": "memx.adapters.mem0:Mem0Adapter",
    "supermemory": "memx.adapters.supermemory:SupermemoryAdapter",
}


def resolve_adapter_path(adapter: str) -> str:
    """Accept a built-in name (`mem0`) or a `module.path:ClassName` import path."""
    key = adapter.strip()
    if ":" in key:
        return key
    try:
        return BUILTIN_ADAPTERS[key.lower()]
    except KeyError:
        available = ", ".join(sorted(BUILTIN_ADAPTERS))
        raise ValueError(
            f"Unknown adapter {adapter!r}. Use a built-in name ({available}) "
            "or module.path:ClassName."
        ) from None
