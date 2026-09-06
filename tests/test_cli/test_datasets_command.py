from __future__ import annotations

from pathlib import Path

from memx.cli.main import app
from tests.test_cli.conftest import LOCOMO, always_pass, mock_judge


ADAPTER = "memx.adapters.mock:MockMemoryAdapter"


def test_datasets_list_shows_builtins(runner, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("MEMX_CACHE_DIR", str(tmp_path / "cache"))
    result = runner.invoke(app, ["datasets", "list"])
    assert result.exit_code == 0, result.output
    assert "locomo" in result.output
    assert "longmemeval" in result.output
    assert "longmemeval-s" in result.output


def test_datasets_pull_writes_cache(runner, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("MEMX_CACHE_DIR", str(tmp_path / "cache"))
    payload = Path(LOCOMO).read_bytes()

    def fake_download(url, dest, *, progress=None):
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(payload)
        if progress is not None:
            progress(len(payload), len(payload))

    monkeypatch.setattr("memx.datasets.fetch.download_url", fake_download)
    result = runner.invoke(app, ["datasets", "pull", "locomo"])
    assert result.exit_code == 0, result.output
    cached = tmp_path / "cache" / "datasets" / "locomo10.json"
    assert cached.exists()
    assert "Saved" in result.output

    again = runner.invoke(app, ["datasets", "pull", "locomo"])
    assert again.exit_code == 0
    assert "Already cached" in again.output


def test_run_without_source_uses_cache(runner, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("MEMX_CACHE_DIR", str(tmp_path / "cache"))
    dest = tmp_path / "cache" / "datasets" / "locomo10.json"
    dest.parent.mkdir(parents=True)
    dest.write_bytes(Path(LOCOMO).read_bytes())
    mock_judge(monkeypatch, always_pass)
    result = runner.invoke(
        app,
        ["run", "--dataset", "locomo", "--adapter", ADAPTER, "--limit", "1"],
    )
    assert result.exit_code == 0, result.output
    assert "locomo10.json" in result.output
    assert dest.exists()
