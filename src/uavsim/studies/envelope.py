"""Linearization envelope: stress a hover-LQR / LQG path by time-scaling missions.

The LQR gains are designed on a hover linearization. Compressing figure-eight
segment times (smaller τ) raises speed and tilt demand until tracking and the
linear KF process model leave the valid region. LQG here means LQR + linear_kf.
"""

from __future__ import annotations

import copy
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import yaml

# Default τ grid: soft linear regime → clear breakdown near ~0.20
DEFAULT_TIME_SCALES: tuple[float, ...] = (1.25, 1.0, 0.75, 0.5, 0.35, 0.25, 0.2, 0.15)

# Showcase / CI may use a shorter grid
SHOWCASE_TIME_SCALES: tuple[float, ...] = (1.0, 0.75, 0.5, 0.35, 0.25, 0.2, 0.15)

LAWS: tuple[tuple[str, str], ...] = (
    ("lqr", "none"),  # full-state LQR
    ("lqg", "linear_kf"),  # LQR + linear KF
)


def scale_waypoint_mission(mission: dict[str, Any], time_scale: float) -> dict[str, Any]:
    """Return a deep-copied mission with all waypoint times multiplied by ``time_scale``."""
    if time_scale <= 0:
        msg = f"time_scale must be positive, got {time_scale}"
        raise ValueError(msg)
    out = copy.deepcopy(mission)
    tau = float(time_scale)
    out["name"] = f"{mission.get('name', 'mission')}_tau{tau:g}"
    desc = mission.get("description") or ""
    out["description"] = f"{desc} [time_scale τ={tau:g}]".strip()
    wps = out.get("waypoints")
    if not isinstance(wps, list):
        msg = "mission must contain a waypoints list"
        raise ValueError(msg)
    for wp in wps:
        wp["time"] = round(float(wp["time"]) * tau, 6)
    return out


def write_scaled_mission(
    base_mission_path: str | Path,
    time_scale: float,
    out_path: str | Path,
) -> Path:
    path = Path(base_mission_path)
    with path.open(encoding="utf-8") as f:
        mission = yaml.safe_load(f)
    scaled = scale_waypoint_mission(mission, time_scale)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        yaml.safe_dump(scaled, f, sort_keys=False)
    return out


def _lqg_observer_block() -> dict[str, Any]:
    return {
        "type": "linear_kf",
        "seed": 7,
        "pos_sigma_m": 0.03,
        "vel_sigma_m_s": 0.05,
        "att_sigma_rad": 0.02,
        "omega_sigma_rad_s": 0.05,
        "process_sigma": 0.03,
        "channels": ["pos", "att", "vel", "omega"],
    }


def build_envelope_study_dict(
    *,
    base_study: dict[str, Any],
    mission_file: str,
    study_id: str,
    law: str,
    observer_type: str,
    position_bound_m: float = 0.75,
) -> dict[str, Any]:
    st = copy.deepcopy(base_study)
    st["study_id"] = study_id
    st.setdefault("guidance", {})["mission_file"] = mission_file
    st.setdefault("metrics", {})["position_bound_m"] = position_bound_m
    st.setdefault("sim", {})
    if observer_type in ("none", "identity"):
        st["sim"]["observer"] = {"type": "none"}
    elif observer_type == "linear_kf":
        st["sim"]["observer"] = _lqg_observer_block()
    else:
        st["sim"]["observer"] = {"type": observer_type}
    # Controller stays lqr_hover for both LQR and LQG
    st.setdefault("controller", {})
    st["controller"]["type"] = st["controller"].get("type") or "lqr_hover"
    st["_envelope"] = {"law": law, "observer": observer_type}
    return st


def run_linearization_envelope(
    *,
    repo_root: str | Path | None = None,
    base_study_path: str | Path = "configs/studies/figure_eight.yaml",
    base_mission_path: str | Path | None = None,
    time_scales: Sequence[float] | None = None,
    laws: Sequence[tuple[str, str]] | None = None,
    output_root: str | Path | None = None,
    position_bound_m: float = 0.75,
) -> dict[str, Any]:
    """
    Run LQR (full-state) and LQG (LQR+KF) on time-scaled figure-eight missions.

    Returns a JSON-serializable envelope document with one point per (τ, law).
    """
    from uavsim.studies import run_nominal_study

    root = Path(repo_root or Path.cwd()).resolve()
    study_path = Path(base_study_path)
    if not study_path.is_file():
        study_path = root / base_study_path
    with study_path.open(encoding="utf-8") as f:
        base_study = yaml.safe_load(f)

    if base_mission_path is None:
        base_mission_path = (base_study.get("guidance", {}) or {}).get(
            "mission_file", "configs/missions/figure_eight.yaml"
        )
    mission_path = Path(base_mission_path)
    if not mission_path.is_file():
        mission_path = root / base_mission_path

    scales = list(time_scales if time_scales is not None else DEFAULT_TIME_SCALES)
    law_list = list(laws if laws is not None else LAWS)
    out = Path(output_root or (root / "runs" / "_envelope")).resolve()
    out.mkdir(parents=True, exist_ok=True)
    missions_dir = out / "missions"
    studies_dir = out / "studies"
    missions_dir.mkdir(exist_ok=True)
    studies_dir.mkdir(exist_ok=True)

    points: list[dict[str, Any]] = []
    for tau in scales:
        miss = write_scaled_mission(mission_path, float(tau), missions_dir / f"tau_{tau:g}.yaml")
        for law, obs in law_list:
            sid = f"envelope_tau{tau:g}_{law}"
            st = build_envelope_study_dict(
                base_study=base_study,
                mission_file=str(miss),
                study_id=sid,
                law=law,
                observer_type=obs,
                position_bound_m=position_bound_m,
            )
            # strip private key before write
            st_write = {k: v for k, v in st.items() if not k.startswith("_")}
            sp = studies_dir / f"{sid}.yaml"
            with sp.open("w", encoding="utf-8") as f:
                yaml.safe_dump(st_write, f, sort_keys=False)
            result = run_nominal_study(sp, output_root=out, run_mc=False)
            m = dict(result.metrics or {})
            points.append(
                {
                    "time_scale": float(tau),
                    "aggressiveness": float(1.0 / tau) if tau else None,
                    "law": law,
                    "observer": obs,
                    "study_id": sid,
                    "run_dir": Path(result.run_dir).name,
                    "success": bool(m.get("success")),
                    "sim_success": bool(m.get("sim_success", True)),
                    "rmse_position_m": m.get("rmse_position_m"),
                    "max_position_error_m": m.get("max_position_error_m"),
                    "rmse_attitude_rad": m.get("rmse_attitude_rad"),
                    "peak_tilt_rad": m.get("peak_tilt_rad"),
                    "peak_tilt_deg": (
                        float(m["peak_tilt_rad"]) * 180.0 / 3.141592653589793
                        if m.get("peak_tilt_rad") is not None
                        else None
                    ),
                    "peak_speed_m_s": m.get("peak_speed_m_s"),
                    "control_effort_proxy": m.get("control_effort_proxy"),
                    "t_final_s": m.get("t_final_s"),
                    "time_in_bounds_frac": m.get("time_in_bounds_frac"),
                }
            )

    # Walk gentle (large τ) → aggressive (small τ); record last success and first fail.
    boundary: dict[str, Any] = {}
    for law, _ in law_list:
        law_pts = sorted(
            [p for p in points if p["law"] == law],
            key=lambda p: -float(p["time_scale"]),
        )
        last_ok: dict[str, Any] | None = None
        first_fail: dict[str, Any] | None = None
        for p in law_pts:
            if p["success"]:
                last_ok = p
            else:
                first_fail = p
                break
        boundary[law] = {
            "last_success_time_scale": last_ok["time_scale"] if last_ok else None,
            "first_fail_time_scale": first_fail["time_scale"] if first_fail else None,
            "last_success_peak_tilt_deg": last_ok.get("peak_tilt_deg") if last_ok else None,
            "first_fail_peak_tilt_deg": first_fail.get("peak_tilt_deg") if first_fail else None,
        }

    return {
        "schema_version": 1,
        "kind": "linearization_envelope",
        "title": "Hover LQR / LQG linearization envelope",
        "description": (
            "Figure-eight mission time scale τ (1 = portfolio path). "
            "Smaller τ shortens segments → higher speed/tilt demand. "
            "LQR = full-state hover LQR; LQG = same LQR on linear KF estimates. "
            "Breakdown marks where hover linearization (+ KF model) lose efficacy."
        ),
        "base_mission": (
            str(mission_path.relative_to(root))
            if mission_path.is_relative_to(root)
            else str(mission_path)
        ),
        "base_study": (
            str(study_path.relative_to(root))
            if study_path.is_relative_to(root)
            else str(study_path)
        ),
        "time_scales": scales,
        "laws": [{"id": a, "observer": b} for a, b in law_list],
        "position_bound_m": position_bound_m,
        "points": points,
        "boundary": boundary,
        "notes": [
            "LQR gains from hover A,B linearization (small-angle).",
            "Classic small-angle validity is often cited near ~15° tilt; "
            "closed-loop success may extend further until tracking fails hard.",
            "LQG uses the same linear A,B for KF predict — mismatch grows with aggression.",
        ],
    }
