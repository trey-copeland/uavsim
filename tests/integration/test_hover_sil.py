"""Integration: closed-loop hover SIL study."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from uavsim.cli.main import main
from uavsim.studies import run_nominal_study

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def runs_tmp(tmp_path: Path) -> Path:
    return tmp_path / "runs"


def test_hover_from_offset_regulates(runs_tmp: Path) -> None:
    study = ROOT / "configs" / "studies" / "hover_from_offset.yaml"
    result = run_nominal_study(study, output_root=runs_tmp)
    assert result.success
    assert result.metrics["final_position_error_m"] < 0.15
    assert result.metrics["rmse_position_m"] < 0.5
    assert (result.run_dir / "nominal" / "metrics.json").is_file()
    assert (result.run_dir / "manifest.yaml").is_file()
    assert (result.run_dir / "nominal" / "timeseries.npz").is_file()
    data = np.load(result.run_dir / "nominal" / "timeseries.npz")
    assert data["x"].shape[1] == 12
    assert data["u"].shape[1] == 4


def test_hover_nominal_cli(runs_tmp: Path) -> None:
    study = ROOT / "configs" / "studies" / "hover_nominal.yaml"
    code = main(["simulate", str(study), "--output", str(runs_tmp)])
    assert code == 0
    runs = list(runs_tmp.glob("hover_nominal_*"))
    assert len(runs) == 1
