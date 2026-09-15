import sqlite3
import sys
from dataclasses import replace
from unittest.mock import patch

import pandas as pd
import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from data_perception_mcp.agent import PerceptionAgent
from data_perception_mcp.cli import main
from data_perception_mcp.config import Settings
from data_perception_mcp.model_manager import resolve_model
from data_perception_mcp.profiling import profile
from data_perception_mcp.security import validate_path


@pytest.fixture
def settings(tmp_path):
    return Settings(allowed_roots=(tmp_path,), max_rows=2)


@pytest.mark.parametrize("suffix", ["csv", "tsv", "json", "jsonl", "parquet", "xlsx", "sqlite"])
def test_formats(tmp_path, settings, suffix):
    frame = pd.DataFrame({"x": [1, 1, 3], "label": ["a", "a", None]})
    path = tmp_path / f"data.{suffix}"
    if suffix in {"csv", "tsv"}:
        frame.to_csv(path, index=False, sep="\t" if suffix == "tsv" else ",")
    elif suffix in {"json", "jsonl"}:
        frame.to_json(path, orient="records", lines=suffix == "jsonl")
    elif suffix == "parquet":
        frame.to_parquet(path, index=False)
    elif suffix == "xlsx":
        frame.to_excel(path, index=False)
    else:
        with sqlite3.connect(path) as connection:
            frame.to_sql('data " quoted', connection, index=False)
    before = path.read_bytes()
    result = profile(path, settings)["tables"][0]
    assert result["rows_analyzed"] == 2
    assert result["rows_truncated"] is True
    assert result["duplicate_rows_in_analyzed_columns"] == 1
    assert result["columns"][0]["mean"] == 1
    assert result["columns"][1]["distinct_non_null"] == 1
    assert path.read_bytes() == before


@pytest.mark.parametrize("suffix", ["json", "parquet"])
def test_nested_values(tmp_path, settings, suffix):
    path = tmp_path / f"nested.{suffix}"
    if suffix == "json":
        path.write_text('[{"x": [1, 2]}, {"x": [1, 2]}]')
    else:
        pd.DataFrame({"x": [[1, 2], [1, 2]]}).to_parquet(path)
    assert profile(path, settings)["tables"][0]["duplicate_rows_in_analyzed_columns"] == 1


def test_missing_and_column_limit(tmp_path, settings):
    path = tmp_path / "data.csv"
    path.write_text("a,b\n1,x\n,y\n")
    table = profile(path, replace(settings, max_columns=1))["tables"][0]
    assert table["columns_truncated"]
    assert table["columns"][0]["missing"] == 1
    assert not table["rows_truncated"]


def test_table_limit(tmp_path, settings):
    path = tmp_path / "data.db"
    with sqlite3.connect(path) as connection:
        for name in ["a", "b"]:
            connection.execute(f"CREATE TABLE {name} (x INTEGER)")
    result = profile(path, replace(settings, max_tables=1))
    assert len(result["tables"]) == 1
    assert result["tables_truncated"]


def test_path_access(tmp_path, settings):
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    outside = tmp_path / "outside.csv"
    outside.write_text("a\n1\n")
    link = allowed / "link.csv"
    link.symlink_to(outside)
    for path in (outside, link, allowed / ".." / "outside.csv"):
        with pytest.raises(PermissionError):
            validate_path(str(path), (allowed,), 100)
    with pytest.raises(PermissionError):
        validate_path(str(outside), (), 100)
    with pytest.raises(ValueError, match="limit"):
        validate_path(str(outside), (tmp_path,), 1)


def test_profile_does_not_load_model(tmp_path, settings):
    path = tmp_path / "data.csv"
    path.write_text("a\n1\n")
    with patch("data_perception_mcp.runtime.resolve_model", side_effect=AssertionError):
        context = PerceptionAgent(settings).build_context("Inspect data", str(path))
    assert "no model inference was performed" in context
    assert '"rows_analyzed": 1' in context


def test_model_settings_and_download(tmp_path):
    with pytest.raises(ValueError):
        Settings(backend="transformers")
    with pytest.raises(ValueError):
        Settings(max_rows=0)
    settings = Settings(model_repo="example/test", revision="abc", cache_dir=str(tmp_path))
    with patch("huggingface_hub.snapshot_download", return_value=str(tmp_path)) as download:
        assert resolve_model(settings) == tmp_path
    assert download.call_args.kwargs["revision"] == "abc"
    assert "*.safetensors" in download.call_args.kwargs["allow_patterns"]
    assert resolve_model(Settings(model_path=str(tmp_path))) == tmp_path


def test_install_preserves_options(tmp_path):
    with (
        patch("data_perception_mcp.cli.shutil.which", return_value="/bin/tool"),
        patch("data_perception_mcp.cli.subprocess.run") as run,
    ):
        main(
            [
                "install",
                "--allow-dir",
                str(tmp_path),
                "--model-repo",
                "example/test",
                "--backend",
                "transformers",
                "--revision",
                "abc",
                "--max-rows",
                "12",
            ]
        )
    command = run.call_args.args[0]
    assert command[:4] == ["codex", "mcp", "add", "data-perception"]
    assert "data-perception-mcp[model] @ git+https://" in command[7]
    assert command[command.index("--allow-dir") + 1] == str(tmp_path.resolve())
    assert command[command.index("--revision") + 1] == "abc"
    assert command[command.index("--max-rows") + 1] == "12"
    assert run.call_args.kwargs["check"] is True


def test_dry_run_has_no_side_effects(tmp_path, capsys):
    with (
        patch("data_perception_mcp.cli.subprocess.run") as run,
        patch("data_perception_mcp.cli.resolve_model") as download,
    ):
        main(
            [
                "install",
                "--allow-dir",
                str(tmp_path),
                "--dry-run",
                "--download-model",
                "--model-repo",
                "example/test",
            ]
        )
    run.assert_not_called()
    download.assert_not_called()
    assert "codex mcp add" in capsys.readouterr().out


def test_install_requires_roots():
    with pytest.raises(SystemExit) as error:
        main(["install", "--dry-run"])
    assert error.value.code == 1


async def test_stdio_protocol(tmp_path):
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    path = allowed / "data.csv"
    path.write_text("x\n1\n2\n")
    outside = tmp_path / "outside.csv"
    outside.write_text("x\n3\n")
    params = StdioServerParameters(
        command=sys.executable,
        args=[
            "-m",
            "data_perception_mcp",
            "serve",
            "--allow-dir",
            str(allowed),
        ],
    )
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        tools = await session.list_tools()
        assert [tool.name for tool in tools.tools] == ["build_data_context"]
        result = await session.call_tool(
            "build_data_context",
            {
                "task": "Inspect data",
                "data_path": str(path),
            },
        )
        payload = result.model_dump(mode="json", exclude_none=True)
        assert payload["isError"] is False
        assert payload["content"][0]["type"] == "text"
        assert "structuredContent" not in payload
        assert "Data Context" in payload["content"][0]["text"]
        for bad_path in [str(outside), str(allowed / "missing.csv")]:
            result = await session.call_tool(
                "build_data_context",
                {
                    "task": "Inspect data",
                    "data_path": bad_path,
                },
            )
            assert result.isError
