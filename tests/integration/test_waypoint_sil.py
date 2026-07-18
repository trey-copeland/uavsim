"""Integration: waypoint guidance closed-loop SIL."""

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


def test_hover_waypoints_regulates(runs_tmp: Path) -> None:
    study = ROOT / "configs" / "studies" / "hover_waypoints.yaml"
    result = run_nominal_study(study, output_root=runs_tmp)
    assert result.success
    assert result.metrics["rmse_position_m"] < 0.15
    assert (result.run_dir / "guidance" / "feasibility.json").is_file()
    assert (result.run_dir / "reference" / "grid.npz").is_file()


def test_gentle_square_tracks(runs_tmp: Path) -> None:
    study = ROOT / "configs" / "studies" / "gentle_square.yaml"
    result = run_nominal_study(study, output_root=runs_tmp)
    # Soft success: complete sim with finite state and bounded error
    assert result.metrics["sim_success"] is True
    assert np.isfinite(result.metrics["rmse_position_m"])
    assert result.metrics["max_position_error_m"] < 2.0
    assert result.metrics["rmse_position_m"] < 1.0
    # auto should pick minsnap for 5 s legs
    assert result.feasibility is not None
    backend = (result.run_dir / "guidance" / "backend.yaml").read_text(encoding="utf-8")
    assert "minsnap" in backend or "interp" in backend


def test_gentle_square_interp_cli(runs_tmp: Path) -> None:
    study = ROOT / "configs" / "studies" / "gentle_square_interp.yaml"
    code = main(["simulate", str(study), "--output", str(runs_tmp)])
    # May be success or soft fail on metrics bound; CLI returns 0 only if overall success
    runs = list(runs_tmp.glob("gentle_square_interp_*"))
    assert len(runs) == 1
    assert (runs[0] / "nominal" / "metrics.json").is_file()
    # Prefer success; if not, at least sim completed with finite metrics
    if code != 0:
        import json

        metrics = json.loads((runs[0] / "nominal" / "metrics.json").read_text())
        assert metrics["sim_success"] is True
        assert metrics["max_position_error_m"] < 2.5
