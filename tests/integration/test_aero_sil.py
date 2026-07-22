"""Closed-loop SIL with aero / ground-effect vehicle configs."""

from __future__ import annotations

from pathlib import Path

from uavsim.studies import run_nominal_study

ROOT = Path(__file__).resolve().parents[2]


def test_figure_eight_aero_tracks(tmp_path: Path) -> None:
    r = run_nominal_study(
        ROOT / "configs" / "studies" / "figure_eight_aero.yaml",
        output_root=tmp_path / "runs",
        run_mc=False,
    )
    assert r.success is True
    assert r.metrics["success"] is True
    assert float(r.metrics["rmse_position_m"]) < 0.15


def test_hover_ground_effect_tracks(tmp_path: Path) -> None:
    r = run_nominal_study(
        ROOT / "configs" / "studies" / "hover_ground_effect.yaml",
        output_root=tmp_path / "runs",
        run_mc=False,
    )
    assert r.metrics["success"] is True
    assert float(r.metrics["rmse_position_m"]) < 0.1
