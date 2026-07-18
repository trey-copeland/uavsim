"""Phase 0: CLI surface smoke tests."""

from __future__ import annotations

import subprocess
import sys

import pytest

from uavsim import __version__
from uavsim.cli.main import build_parser, main


def test_build_parser_has_expected_subcommands() -> None:
    parser = build_parser()
    # argparse stores subparsers actions; check help text instead
    help_text = parser.format_help()
    for name in (
        "simulate",
        "study",
        "mc-shard",
        "mc-merge",
        "report",
        "export-controller",
        "compare",
        "hil",
    ):
        assert name in help_text


def test_main_no_args_prints_help(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([]) == 0
    out = capsys.readouterr().out
    assert "uavsim" in out
    assert "simulate" in out


def test_main_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_study_missing_file_returns_1(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["study", "does_not_exist.yaml"]) == 1
    assert "not found" in capsys.readouterr().err


def test_report_missing_dir_returns_1(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["report", "does_not_exist_run"]) == 1
    assert "not found" in capsys.readouterr().err


def test_compare_missing_dirs_returns_1(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["compare", "a", "b"]) == 1
    assert "exist" in capsys.readouterr().err


def test_simulate_missing_file_returns_1(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["simulate", "does_not_exist.yaml"]) == 1
    assert "not found" in capsys.readouterr().err


def test_console_script_help() -> None:
    """Exercise installed entry point when available; else module -m path."""
    result = subprocess.run(
        [sys.executable, "-m", "uavsim.cli.main", "--help"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "simulate" in result.stdout
