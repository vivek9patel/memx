from __future__ import annotations

import os
import urllib.request
from collections.abc import Callable
from pathlib import Path

from memx.datasets.catalog import DatasetSpec, get_spec
from memx.exceptions import MemxError

_CHUNK = 256 * 1024
_USER_AGENT = "memx/0.1"

ProgressFn = Callable[[int, int | None], None]


def cache_dir() -> Path:
    """Dataset cache. Override with MEMX_CACHE_DIR (files go in <dir>/datasets)."""
    override = os.environ.get("MEMX_CACHE_DIR")
    if override:
        return Path(override).expanduser() / "datasets"
    return Path.home() / ".cache" / "memx" / "datasets"


def cached_path(spec: DatasetSpec) -> Path:
    return cache_dir() / spec.filename


def download_url(url: str, dest: Path, *, progress: ProgressFn | None = None) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".tmp")
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    try:
        with urllib.request.urlopen(request) as response:
            total_header = response.headers.get("Content-Length")
            total = int(total_header) if total_header and total_header.isdigit() else None
            received = 0
            with tmp.open("wb") as handle:
                while True:
                    chunk = response.read(_CHUNK)
                    if not chunk:
                        break
                    handle.write(chunk)
                    received += len(chunk)
                    if progress is not None:
                        progress(received, total)
    except OSError as exc:
        if tmp.exists():
            tmp.unlink(missing_ok=True)
        raise MemxError(f"Failed to download {url}: {exc}") from exc
    except Exception:
        if tmp.exists():
            tmp.unlink(missing_ok=True)
        raise
    tmp.replace(dest)


def ensure_dataset(
    dataset_name: str,
    *,
    source: Path | str | None = None,
    force: bool = False,
    progress: ProgressFn | None = None,
) -> Path:
    """Return a local JSON path: explicit --source, else cached official file (downloaded if missing)."""
    if source is not None:
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"Dataset source not found: {path}")
        return path

    spec = get_spec(dataset_name)
    dest = cached_path(spec)
    if dest.exists() and dest.stat().st_size > 0 and not force:
        return dest
    download_url(spec.url, dest, progress=progress)
    if not dest.exists() or dest.stat().st_size == 0:
        raise MemxError(f"Download produced an empty file for '{dataset_name}': {dest}")
    return dest
