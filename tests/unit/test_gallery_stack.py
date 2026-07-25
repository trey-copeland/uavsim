"""Unit tests for closed-loop stack provenance (showcase System tab)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from uavsim.viz.gallery import run_to_gallery_entry
from uavsim.viz.stack import (
    DEFAULT_EDGES,
    build_stack_from_run_dir,
    build_stack_from_study_mapping,
)

ROOT = Path(__file__).resolve().parents[2]
STUDIES = ROOT / "configs" / "studies"
RUNS = ROOT / "runs"

_EDGE_PAIRS = {tuple(e) for e in DEFAULT_EDGES}


def _load_study(name: str) -> dict:
    path = STUDIES / name
    if not path.is_file():
        pytest.skip(f"study config missing: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def _first_run_matching(*substrings: str) -> Path | None:
    if not RUNS.is_dir():
        return None
    for p in sorted(RUNS.iterdir()):
        if not p.is_dir():
            continue
        if all(s in p.name for s in substrings) and (p / "study_config.yaml").is_file():
            return p
    return None


def test_ideal_lqr_from_study_config() -> None:
    study = _load_study("figure_eight.yaml")
    vehicle = yaml.safe_load(
        (ROOT / "configs" / "vehicles" / "default_quadrotor.yaml").read_text(encoding="utf-8")
    )
    mission = yaml.safe_load(
        (ROOT / "configs" / "missions" / "figure_eight.yaml").read_text(encoding="utf-8")
    )
    stack = build_stack_from_study_mapping(
        study,
        vehicle=vehicle,
        mission=mission,
        gallery_id="figure_eight_lqr",
        repo_root=ROOT,
    )
    assert stack["schema_version"] == 1
    assert stack["topology"] == "closed_loop_sil"
    node_ids = [n["id"] for n in stack["nodes"]]
    assert node_ids == [
        "mission",
        "guidance",
        "sensors",
        "observer",
        "controller",
        "actuators",
        "plant",
        "metrics",
    ]
    edge_set = {tuple(e) for e in stack["edges"]}
    assert edge_set >= _EDGE_PAIRS

    d = stack["details"]
    assert d["controller"]["type"] == "lqr_hover"
    assert d["controller"]["gains"] is not None
    assert "Q_diag" in d["controller"]["gains"]
    assert d["controller"]["equation"]
    assert d["controller"]["equations"]["lines"]
    assert any("CARE" in ln or "K =" in ln for ln in d["controller"]["equations"]["lines"])
    assert d["plant"]["equations"]["lines"]
    assert any("ṗ" in ln or "p" in ln for ln in d["plant"]["equations"]["lines"])
    assert d["observer"]["equations"]["lines"]
    assert any("x̂" in ln or "true" in ln.lower() for ln in d["observer"]["equations"]["lines"])
    assert d["plant"]["linearization"] is not None
    assert len(d["plant"]["linearization"]["A"]) == 12
    assert len(d["plant"]["linearization"]["B"][0]) == 4
    assert d["controller"]["linearization"] is not None
    assert d["controller"]["linearization"]["A"] == d["plant"]["linearization"]["A"]
    assert (
        d["observer"]["observer_type"] in (None, "none") or d["observer"]["observer_type"] == "none"
    )
    # Ideal study omits observer block → defaulted to none
    obs_node = next(n for n in stack["nodes"] if n["id"] == "observer")
    assert "identity" in obs_node["summary"].lower() or obs_node["badges"] == ["none"]
    assert d["plant"]["plant_mode"] == "wrench"
    assert d["actuators"]["plant_mode"] == "wrench"
    assert d["mission"]["mission_file"] == "configs/missions/figure_eight.yaml"
    assert d["mission"]["n_waypoints"] == 9
    assert d["identity"]["gallery_id"] == "figure_eight_lqr"
    assert d["identity"]["study_id"] == "figure_eight"


def test_gps_imu_lqg_observer_channels() -> None:
    study = _load_study("figure_eight_gps_imu_lqg.yaml")
    stack = build_stack_from_study_mapping(study, repo_root=ROOT)
    d = stack["details"]
    assert d["observer"]["observer_type"] == "linear_kf"
    assert d["observer"]["channels"] == ["pos", "omega"]
    assert d["sensors"]["channels"] == ["pos", "omega"]
    assert any("Kalman" in ln or "K =" in ln for ln in d["observer"]["equations"]["lines"])
    assert d["observer"]["linearization"] is not None
    assert d["observer"]["linearization"]["shape_A"] == [12, 12]
    assert d["controller"]["type"] == "lqr_hover"
    obs_node = next(n for n in stack["nodes"] if n["id"] == "observer")
    assert "linear_kf" in (obs_node.get("badges") or [])


def test_pid_cascade_gains_without_k() -> None:
    study = _load_study("figure_eight_pid.yaml")
    stack = build_stack_from_study_mapping(study, repo_root=ROOT)
    d = stack["details"]
    assert d["controller"]["type"] == "pid_cascade"
    gains = d["controller"]["gains"] or {}
    assert "kp_pos" in gains
    assert "kd_rate" in gains
    assert "K" not in gains


def test_motors_plant_mode() -> None:
    study = _load_study("figure_eight_motors_mc.yaml")
    vehicle = yaml.safe_load(
        (ROOT / "configs" / "vehicles" / "default_quadrotor.yaml").read_text(encoding="utf-8")
    )
    stack = build_stack_from_study_mapping(study, vehicle=vehicle, repo_root=ROOT)
    assert stack["details"]["actuators"]["plant_mode"] == "motors"
    assert stack["details"]["plant"]["plant_mode"] == "motors"
    act = next(n for n in stack["nodes"] if n["id"] == "actuators")
    assert "motors" in (act.get("badges") or [])
    mixer = stack["details"]["actuators"]["mixer"]
    assert mixer is not None
    assert mixer.get("layout") == "x"


def test_build_stack_from_run_dir_pid() -> None:
    run = _first_run_matching("figure_eight_pid")
    if run is None:
        pytest.skip("no figure_eight_pid run under runs/")
    stack = build_stack_from_run_dir(run, gallery_id="figure_eight_pid")
    assert stack["schema_version"] == 1
    assert stack["details"]["controller"]["type"] == "pid_cascade"
    # frozen study_config often has absolute mission path → relativized
    mf = stack["details"]["mission"]["mission_file"]
    assert mf is None or mf.startswith("configs/") or "figure_eight" in str(mf)
    assert stack["details"]["identity"]["source_run"] == run.name
    assert stack["details"]["identity"]["gallery_id"] == "figure_eight_pid"
    assert stack["details"]["observer"]["observer_type"] == "none"
    # artifact should supply u_hover
    assert stack["details"]["controller"]["u_hover"] is not None


def test_gallery_entry_includes_stack() -> None:
    run = _first_run_matching("figure_eight_pid")
    if run is None:
        pytest.skip("no figure_eight_pid run under runs/")
    entry = run_to_gallery_entry(run, gallery_id="figure_eight_pid", role="ideal_pid")
    assert "stack" in entry
    assert entry["stack"] is not None
    assert entry["stack"]["schema_version"] == 1
    assert entry["stack"]["details"]["controller"]["type"] == "pid_cascade"


def test_naive_partial_raw_notes() -> None:
    study = _load_study("figure_eight_gps_imu_naive.yaml")
    stack = build_stack_from_study_mapping(study, repo_root=ROOT)
    assert stack["details"]["observer"]["observer_type"] == "partial_raw"
    assert stack["details"]["observer"]["notes"]
    assert "naive" in stack["details"]["observer"]["notes"].lower()
