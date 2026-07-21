"""Linearization envelope helpers and short sweep smoke."""

from __future__ import annotations

from pathlib import Path

import yaml

from uavsim.studies.envelope import (
    build_envelope_study_dict,
    run_linearization_envelope,
    scale_waypoint_mission,
)

ROOT = Path(__file__).resolve().parents[2]


def test_scale_waypoint_mission_times() -> None:
    with (ROOT / "configs" / "missions" / "figure_eight.yaml").open(encoding="utf-8") as f:
        mission = yaml.safe_load(f)
    scaled = scale_waypoint_mission(mission, 0.5)
    assert scaled["waypoints"][0]["time"] == 0.0
    assert abs(scaled["waypoints"][-1]["time"] - 16.0) < 1e-9
    # original unchanged
    assert mission["waypoints"][-1]["time"] == 32.0


def test_build_envelope_study_lqg_observer() -> None:
    with (ROOT / "configs" / "studies" / "figure_eight.yaml").open(encoding="utf-8") as f:
        base = yaml.safe_load(f)
    st = build_envelope_study_dict(
        base_study=base,
        mission_file="configs/missions/figure_eight.yaml",
        study_id="t",
        law="lqg",
        observer_type="linear_kf",
    )
    assert st["sim"]["observer"]["type"] == "linear_kf"
    assert st["controller"]["type"] == "lqr_hover"


def test_envelope_sweep_smoke(tmp_path: Path) -> None:
    doc = run_linearization_envelope(
        repo_root=ROOT,
        time_scales=(1.0, 0.2),
        output_root=tmp_path / "env",
    )
    assert doc["kind"] == "linearization_envelope"
    assert len(doc["points"]) == 4  # 2 scales × 2 laws
    laws = {p["law"] for p in doc["points"]}
    assert laws == {"lqr", "lqg"}
    # gentle point should succeed; aggressive may fail — still finite metrics for lqr
    gentle = [p for p in doc["points"] if p["time_scale"] == 1.0 and p["law"] == "lqr"][0]
    assert gentle["success"] is True
    assert gentle["peak_tilt_rad"] is not None
    assert "lqr" in doc["boundary"]
