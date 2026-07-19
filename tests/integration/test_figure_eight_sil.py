"""Soft validation: LQR figure-eight near ME590 heritage RMSE band."""

from __future__ import annotations

from pathlib import Path

from uavsim.studies import run_nominal_study

ROOT = Path(__file__).resolve().parents[2]


def test_figure_eight_lqr_tracks_near_heritage_band(tmp_path: Path) -> None:
    """
    Heritage ME590 figure_eight_long (flat, constant yaw):
      minsnap LQR position RMSE ~0.038 m, makima ~0.028 m.
    Elevated figure_eight mission is not bit-identical; require success and
    RMSE in a soft band that fails only on gross regressions.
    """
    result = run_nominal_study(
        ROOT / "configs" / "studies" / "figure_eight.yaml",
        output_root=tmp_path / "runs",
        run_mc=False,
    )
    m = result.metrics
    assert m["success"] is True
    rmse = float(m["rmse_position_m"])
    assert rmse < 0.12, f"position RMSE {rmse} m outside soft band"
    assert rmse > 0.005, f"position RMSE {rmse} m suspiciously low"
    max_e = float(m["max_position_error_m"])
    assert max_e < 0.25, f"max position error {max_e} m too large"
