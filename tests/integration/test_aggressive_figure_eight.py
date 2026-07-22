"""Phase 5c.3b: aggressive elevated figure-eight stress demo."""

from __future__ import annotations

from pathlib import Path

from uavsim.studies import run_nominal_study

ROOT = Path(__file__).resolve().parents[2]
STUDY = ROOT / "configs" / "studies" / "figure_eight_aggressive.yaml"


def test_aggressive_figure_eight_quat_tracks(tmp_path: Path) -> None:
    """
    Faster path + altitude undulation under LQR + quat plant.
    Soft upper band catches divergence; with correct attitude feedforward,
    RMSE can be low even on the stress path (ideal full-state).
    """
    result = run_nominal_study(STUDY, output_root=tmp_path / "runs", run_mc=False)
    m = result.metrics
    assert m["success"] is True
    assert result.success is True
    rmse = float(m["rmse_position_m"])
    assert rmse < 0.5, f"RMSE {rmse} m out of soft band"
    # Stress case should not look like pure hover (envelope, not RMSE floor)
    assert float(m["peak_speed_m_s"]) > 0.5
    assert m.get("attitude_error_model") == "so3_geodesic"
