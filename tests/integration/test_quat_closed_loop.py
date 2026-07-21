"""Closed-loop quaternion plant vs Euler plant (Phase 5c)."""

from __future__ import annotations

from pathlib import Path

import yaml

from uavsim.studies import run_nominal_study

ROOT = Path(__file__).resolve().parents[2]


def test_figure_eight_euler_still_tracks(tmp_path: Path) -> None:
    result = run_nominal_study(
        ROOT / "configs" / "studies" / "figure_eight.yaml",
        output_root=tmp_path / "runs",
        run_mc=False,
    )
    assert result.metrics["success"] is True
    assert float(result.metrics["rmse_position_m"]) < 0.12
    assert result.metrics.get("attitude_error_model") == "so3_geodesic"


def test_figure_eight_quat_plant_tracks(tmp_path: Path) -> None:
    """Optional sim.attitude: quat — controllers still on Euler measurements."""
    src = ROOT / "configs" / "studies" / "figure_eight.yaml"
    cfg = yaml.safe_load(src.read_text(encoding="utf-8"))
    cfg["study_id"] = "figure_eight_quat"
    cfg.setdefault("sim", {})
    cfg["sim"]["attitude"] = "quat"
    cfg_path = tmp_path / "figure_eight_quat.yaml"
    cfg_path.write_text(yaml.safe_dump(cfg), encoding="utf-8")

    result = run_nominal_study(cfg_path, output_root=tmp_path / "runs", run_mc=False)
    assert result.success is True
    assert result.metrics["success"] is True
    rmse = float(result.metrics["rmse_position_m"])
    assert rmse < 0.15, f"quat plant RMSE {rmse}"
    # Near Euler baseline (~0.037 m)
    assert rmse < 0.08


def test_euler_and_quat_plants_close_on_figure_eight(tmp_path: Path) -> None:
    r_e = run_nominal_study(
        ROOT / "configs" / "studies" / "figure_eight.yaml",
        output_root=tmp_path / "runs_e",
        run_mc=False,
    )
    src = ROOT / "configs" / "studies" / "figure_eight.yaml"
    cfg = yaml.safe_load(src.read_text(encoding="utf-8"))
    cfg["study_id"] = "figure_eight_quat_cmp"
    cfg.setdefault("sim", {})
    cfg["sim"]["attitude"] = "quat"
    cfg_path = tmp_path / "f8q.yaml"
    cfg_path.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    r_q = run_nominal_study(cfg_path, output_root=tmp_path / "runs_q", run_mc=False)

    pe = float(r_e.metrics["rmse_position_m"])
    pq = float(r_q.metrics["rmse_position_m"])
    # Same mission/controller; integrators differ (RK45 vs RK4) — soft band
    assert abs(pe - pq) < 0.02, f"euler {pe} vs quat {pq}"
