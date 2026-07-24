"""Linearization envelope helpers and short sweep smoke."""

from __future__ import annotations

from pathlib import Path

import yaml

from uavsim.studies.envelope import (
    MATRIX_SCHEMES,
    build_envelope_study_dict,
    build_envelope_study_from_scheme,
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


def test_build_envelope_study_from_scheme_pid() -> None:
    sch = next(s for s in MATRIX_SCHEMES if s.id == "ideal_pid")
    with (ROOT / sch.study_rel).open(encoding="utf-8") as f:
        base = yaml.safe_load(f)
    st = build_envelope_study_from_scheme(
        scheme_study=base,
        scheme=sch,
        mission_file="configs/missions/figure_eight.yaml",
        study_id="edge_pid",
        position_bound_m=0.75,
    )
    assert st["controller"]["type"] == "pid_cascade"
    assert st["metrics"]["position_bound_m"] == 0.75
    assert st["guidance"]["mission_file"].endswith("figure_eight.yaml")


def test_envelope_sweep_smoke(tmp_path: Path) -> None:
    # Small subset: ideal LQR + ideal PID + GPS+IMU LQG at two τ
    subset = [s for s in MATRIX_SCHEMES if s.id in ("ideal_lqr", "ideal_pid", "gps_imu_lqg")]
    doc = run_linearization_envelope(
        repo_root=ROOT,
        time_scales=(1.0, 0.25),
        schemes=subset,
        output_root=tmp_path / "env",
    )
    assert doc["kind"] == "linearization_envelope"
    assert doc["schema_version"] >= 2
    assert len(doc["points"]) == 6  # 2 scales × 3 schemes
    laws = {p["law"] for p in doc["points"]}
    assert laws == {"ideal_lqr", "ideal_pid", "gps_imu_lqg"}
    assert all(p.get("family") in ("lqr", "pid") for p in doc["points"])
    gentle = [p for p in doc["points"] if p["time_scale"] == 1.0 and p["law"] == "ideal_lqr"][0]
    assert gentle["success"] is True
    assert gentle["label"] == "Ideal LQR"
    assert "ideal_lqr" in doc["boundary"]
    assert len(doc["schemes"]) == 3


def test_envelope_legacy_laws_map(tmp_path: Path) -> None:
    doc = run_linearization_envelope(
        repo_root=ROOT,
        time_scales=(1.0,),
        laws=(("lqr", "none"), ("lqg", "linear_kf")),
        output_root=tmp_path / "env_legacy",
    )
    laws = {p["law"] for p in doc["points"]}
    assert laws == {"ideal_lqr", "gps_imu_lqg"}
