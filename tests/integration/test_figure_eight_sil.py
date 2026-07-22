"""Soft validation: LQR figure-eight near ME590 heritage RMSE band."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from uavsim.studies import run_nominal_study

ROOT = Path(__file__).resolve().parents[2]


def test_figure_eight_lqr_tracks_near_heritage_band(tmp_path: Path) -> None:
    """
    Full-state LQR on figure-eight with correct attitude feedforward should
    track tightly (often well under 1 cm RMSE). Soft upper band catches
    regressions; success flag enforces portfolio honesty bounds.
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
    assert np.isfinite(rmse) and rmse >= 0.0
    max_e = float(m["max_position_error_m"])
    assert max_e < 0.25, f"max position error {max_e} m too large"
