"""Unit tests: reference feasibility (auto-yaw stress case)."""

from __future__ import annotations

from pathlib import Path

from uavsim.guidance.waypoints import generate_interp_trajectory, load_mission
from uavsim.reference import check_sampled_feasibility
from uavsim.vehicles.params import default_vehicle

ROOT = Path(__file__).resolve().parents[2]
MISSIONS = ROOT / "configs" / "missions"


def test_constant_yaw_gentle_is_ok() -> None:
    m = load_mission(MISSIONS / "gentle_square.yaml")
    ref = generate_interp_trajectory(m, yaw_mode="constant")
    report = check_sampled_feasibility(ref, default_vehicle())
    yaw_fails = [i for i in report.issues if i.code.startswith("yaw") and i.severity == "fail"]
    assert not yaw_fails


def test_path_tangent_figure_eight_flags_yaw() -> None:
    """Heritage lesson: auto-yaw on tight curves produces high yaw rates."""
    m = load_mission(MISSIONS / "figure_eight_auto_yaw.yaml")
    ref = generate_interp_trajectory(m, yaw_mode="path_tangent", dt_s=0.02)
    report = check_sampled_feasibility(ref, default_vehicle())
    yaw_issues = [i for i in report.issues if "yaw" in i.code]
    assert yaw_issues, f"expected yaw issues, got summary={report.summary}"
    # At least a warn or fail on peak or rms yaw rate
    codes = {i.code for i in yaw_issues}
    assert codes & {"yaw_rate_peak", "yaw_rate_rms", "yaw_accel"}
