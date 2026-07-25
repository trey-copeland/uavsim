"""End-to-end online intercept_pursue: capture + sane tracking metrics."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from uavsim.studies import run_nominal_study

ROOT = Path(__file__).resolve().parents[2]


def test_online_intercept_commanded_tracking_and_capture(tmp_path: Path) -> None:
    """
    Hero online study must replan, capture, and report tracking RMSE vs the
    piecewise commanded reference (not the final segment alone).

    Historical bug: post-hoc evaluate of adapter.reference (last segment only)
    produced rmse_position_m ~ 30 m and success=false with no diagnostic value.
    """
    result = run_nominal_study(
        ROOT / "configs" / "studies" / "tutorials" / "intercept_online_success.yaml",
        output_root=tmp_path / "runs",
        run_mc=False,
    )
    m = result.metrics
    assert m.get("tracking_vs_commanded_reference") is True
    n_replans = int(m.get("n_replans") or 0)
    assert n_replans >= 5, f"expected online replan, got n_replans={n_replans}"

    # Capture story (independent of tracking)
    assert m.get("intercept_success") is True
    min_range = float(m["min_range_m"])
    assert np.isfinite(min_range) and min_range <= 1.0 + 1e-6

    # Tracking vs commanded x_r must be finite and far below the ~30 m clamp bug
    rmse = float(m["rmse_position_m"])
    max_e = float(m["max_position_error_m"])
    assert np.isfinite(rmse) and np.isfinite(max_e)
    assert rmse < 5.0, f"rmse_position_m={rmse} still looks like final-segment clamp"
    assert max_e < 15.0, f"max_position_error_m={max_e} unreasonably large for commanded ref"

    # Artifact grid should span full mission, not only last ~0.2 s
    grid = np.load(result.run_dir / "reference" / "grid.npz")
    t_ref = np.asarray(grid["t"], dtype=float)
    assert t_ref[0] <= 0.05
    assert t_ref[-1] >= 9.0
    x_ref0 = np.asarray(grid["x"][0, 0:3], dtype=float)
    # Seed/takeoff neighborhood (pad), not intercept endpoint ~ tens of meters away
    assert float(np.linalg.norm(x_ref0)) < 8.0, f"x_ref[0]={x_ref0} not near pad"
