from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest

from memx.datasets.catalog import get_spec
from memx.datasets.fetch import cached_path, download_url, ensure_dataset
from memx.exceptions import MemxError

FIXTURES = Path(__file__).parent / "fixtures"
LOCOMO_SAMPLE = FIXTURES / "locomo_sample.json"


@pytest.fixture(autouse=True)
def isolate_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("MEMX_CACHE_DIR", str(tmp_path / "cache"))
    return tmp_path / "cache" / "datasets"


class _FakeResponse:
    def __init__(self, payload: bytes) -> None:
        self._buf = BytesIO(payload)
        self.headers = {"Content-Length": str(len(payload))}

    def read(self, size: int = -1) -> bytes:
        return self._buf.read(size)

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None


def test_get_spec_unknown_lists_builtins() -> None:
    with pytest.raises(MemxError, match="locomo"):
        get_spec("nope")


def test_ensure_dataset_uses_explicit_source(isolate_cache: Path) -> None:
    path = ensure_dataset("locomo", source=LOCOMO_SAMPLE)
    assert path == LOCOMO_SAMPLE
    assert not (isolate_cache / "locomo10.json").exists()


def test_ensure_dataset_downloads_when_missing(
    isolate_cache: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = LOCOMO_SAMPLE.read_bytes()

    def fake_urlopen(request, timeout=None):  # noqa: ANN001
        assert "locomo10.json" in request.full_url
        return _FakeResponse(payload)

    monkeypatch.setattr("memx.datasets.fetch.urllib.request.urlopen", fake_urlopen)
    path = ensure_dataset("locomo")
    assert path == cached_path(get_spec("locomo"))
    assert path.read_bytes() == payload


def test_ensure_dataset_reuses_cache(isolate_cache: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dest = cached_path(get_spec("locomo"))
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(b'[{"ok": true}]')
    monkeypatch.setattr(
        "memx.datasets.fetch.urllib.request.urlopen",
        lambda *_a, **_k: pytest.fail("should not download"),
    )
    assert ensure_dataset("locomo") == dest


def test_download_url_cleans_tmp_on_failure(
    isolate_cache: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dest = isolate_cache / "broken.json"

    def boom(*_a, **_k):
        raise OSError("network down")

    monkeypatch.setattr("memx.datasets.fetch.urllib.request.urlopen", boom)
    with pytest.raises(MemxError, match="Failed to download"):
        download_url("https://example.invalid/x.json", dest)
    assert not dest.exists()
    assert not dest.with_name(dest.name + ".tmp").exists()


def test_longmemeval_aliases_share_oracle_file() -> None:
    assert get_spec("longmemeval").filename == get_spec("longmemeval-oracle").filename
    assert get_spec("longmemeval-s").loader_name == "longmemeval"
    assert get_spec("longmemeval-m").loader_name == "longmemeval"
