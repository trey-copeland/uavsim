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


def test_unimplemented_study_returns_2(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["study"]) == 2
    err = capsys.readouterr().err
    assert "not implemented" in err
    assert "Phase 3" in err


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
