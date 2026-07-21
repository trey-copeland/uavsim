"""SIL with mixer + first-order motors (D-7/D-8)."""

from __future__ import annotations

from pathlib import Path

from uavsim.studies import run_nominal_study

ROOT = Path(__file__).resolve().parents[2]


def test_figure_eight_motors_tracks(tmp_path: Path) -> None:
    r = run_nominal_study(
        ROOT / "configs" / "studies" / "figure_eight_motors.yaml",
        output_root=tmp_path / "runs",
        run_mc=False,
    )
    assert r.success is True
    assert r.metrics["success"] is True
    # Slightly softer than ideal wrench plant (~0.037)
    assert float(r.metrics["rmse_position_m"]) < 0.15
