"""Phase 5d: closed-loop with linear KF observer."""

from __future__ import annotations

from pathlib import Path

from uavsim.studies import run_nominal_study

ROOT = Path(__file__).resolve().parents[2]


def test_figure_eight_full_state_still_ok(tmp_path: Path) -> None:
    r = run_nominal_study(
        ROOT / "configs" / "studies" / "figure_eight.yaml",
        output_root=tmp_path / "runs",
        run_mc=False,
    )
    assert r.metrics["success"] is True
    assert r.metrics.get("observer_id", "none") in ("none", "none")
    assert float(r.metrics["rmse_position_m"]) < 0.12


def test_figure_eight_linear_kf_tracks(tmp_path: Path) -> None:
    r = run_nominal_study(
        ROOT / "configs" / "studies" / "figure_eight_observer.yaml",
        output_root=tmp_path / "runs",
        run_mc=False,
    )
    assert r.success is True
    assert r.metrics["success"] is True
    assert r.metrics["observer_id"] == "linear_kf"
    rmse = float(r.metrics["rmse_position_m"])
    # Degraded vs full-state (~0.037) but still bounded
    assert rmse < 0.4, f"observer SIL RMSE {rmse}"
    assert "rmse_estimate_position_m" in r.metrics
