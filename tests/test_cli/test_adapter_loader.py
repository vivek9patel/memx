from __future__ import annotations

import pytest
from typer.testing import CliRunner

from memx.adapters.mock import MockMemoryAdapter
from memx.adapters.registry import resolve_adapter_path
from memx.cli.adapter_loader import load_adapter
from memx.cli.main import app


def test_load_adapter_short_name_mock() -> None:
    adapter = load_adapter("mock")
    assert isinstance(adapter, MockMemoryAdapter)


def test_load_adapter_unknown_short_name() -> None:
    with pytest.raises(ValueError, match="Unknown adapter"):
        resolve_adapter_path("not-a-provider")
    with pytest.raises(Exception, match="Unknown adapter"):
        load_adapter("not-a-provider")


def test_run_help_lists_builtin_adapters() -> None:
    result = CliRunner().invoke(app, ["run", "--help"])
    assert result.exit_code == 0
    assert "mem0" in result.output
    assert "supermemory" in result.output
    assert "mock" in result.output
