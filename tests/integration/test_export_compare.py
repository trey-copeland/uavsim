"""Integration: export round-trip SIL, compare two runs, PID study."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from uavsim.cli.main import main
from uavsim.control import controller_from_artifact, load_controller_artifact
from uavsim.sim import InProcessControllerAdapter, SimPlant, simulate_closed_loop
from uavsim.studies import run_nominal_study
from uavsim.vehicles.params import load_vehicle
from uavsim.viz import compare_runs

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def runs_tmp(tmp_path: Path) -> Path:
    return tmp_path / "runs"


def test_export_round_trip_sil(runs_tmp: Path) -> None:
    study = ROOT / "configs" / "studies" / "hover_from_offset.yaml"
    result = run_nominal_study(study, output_root=runs_tmp, run_mc=False)
    assert result.success
    art_path = result.run_dir / "nominal" / "controller_artifact.yaml"
    assert art_path.is_file()

    out = runs_tmp / "ctrl.yaml"
    code = main(["export-controller", str(result.run_dir), "--out", str(out)])
    assert code == 0
    art = load_controller_artifact(out)
    ctrl = controller_from_artifact(art)

    # Reload vehicle from study vehicle path for plant
    vehicle = load_vehicle(ROOT / "configs" / "vehicles" / "default_quadrotor.yaml")
    # Use same reference as study via timeseries start
    from uavsim.reference import hold_at_ned

    reference = hold_at_ned(np.zeros(3), duration_s=2.0)
    plant = SimPlant(vehicle)
    adapter = InProcessControllerAdapter(ctrl, reference)
    x0 = reference.evaluate(0.0).x_ref.copy()
    x0[0] = 0.2
    sim = simulate_closed_loop(plant, adapter, t0=0.0, tf=2.0, x0=x0, max_step=0.02)
    assert sim.success
    assert np.isfinite(sim.x).all()


def test_pid_hover_from_offset(runs_tmp: Path) -> None:
    study = ROOT / "configs" / "studies" / "hover_pid.yaml"
    result = run_nominal_study(study, output_root=runs_tmp, run_mc=False)
    assert result.metrics["sim_success"] is True
    assert result.metrics["final_position_error_m"] < 0.35
    assert (result.run_dir / "nominal" / "controller_artifact.yaml").is_file()


def test_compare_lqr_vs_pid(runs_tmp: Path) -> None:
    lqr = run_nominal_study(
        ROOT / "configs" / "studies" / "gentle_square.yaml",
        output_root=runs_tmp / "lqr",
        run_mc=False,
    )
    pid = run_nominal_study(
        ROOT / "configs" / "studies" / "compare_lqr_vs_pid.yaml",
        output_root=runs_tmp / "pid",
        run_mc=False,
    )
    assert lqr.metrics["sim_success"] is True
    assert pid.metrics["sim_success"] is True

    cmp = compare_runs(
        lqr.run_dir,
        pid.run_dir,
        output_dir=runs_tmp / "compare_out",
        figures=False,
    )
    assert cmp.summary_md.is_file()
    assert cmp.delta_json.is_file()
    assert "rmse_position_m" in cmp.summary_md.read_text(encoding="utf-8")

    code = main(
        [
            "compare",
            str(lqr.run_dir),
            str(pid.run_dir),
            "--output",
            str(runs_tmp / "compare_cli"),
            "--no-figures",
        ]
    )
    assert code == 0
