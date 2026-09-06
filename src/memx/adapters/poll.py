from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TypeVar

T = TypeVar("T")
R = TypeVar("R")


def run_parallel(fn: Callable[[T], None], items: list[T], *, max_workers: int = 16) -> None:
    """Run ``fn`` on each item, concurrently when there is more than one."""
    if not items:
        return
    if len(items) == 1:
        fn(items[0])
        return
    workers = max(1, min(max_workers, len(items)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(fn, item) for item in items]
        for future in futures:
            future.result()


def map_parallel(fn: Callable[[T], R], items: list[T], *, max_workers: int = 16) -> dict[T, R]:
    """Apply ``fn`` to each item, concurrently when there is more than one."""
    if not items:
        return {}
    if len(items) == 1:
        item = items[0]
        return {item: fn(item)}
    workers = max(1, min(max_workers, len(items)))
    mapped: dict[T, R] = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(fn, item): item for item in items}
        for future in as_completed(futures):
            item = futures[future]
            mapped[item] = future.result()
    return mapped
