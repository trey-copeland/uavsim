"""Linearization / tracking envelope: time-scale stress on portfolio schemes.

Compressing figure-eight segment times (smaller τ) raises speed and tilt demand.
Each **scheme** is a controller × sensor stack from the teaching matrix (ideal LQR,
cascade PID, GPS+IMU naive/KF, AHRS, flow+alt, IMU-only). Gains and observers are
loaded from the committed portfolio study YAMLs so the envelope matches the matrix.
"""

from __future__ import annotations

import copy
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

# Default τ grid: soft linear regime → densified knee → hard breakdown.
DEFAULT_TIME_SCALES: tuple[float, ...] = (
    1.25,
    1.0,
    0.75,
    0.5,
    0.4,
    0.35,
    0.32,
    0.3,
    0.28,
    0.26,
    0.25,
    0.22,
    0.2,
    0.18,
    0.16,
    0.15,
    0.14,
    0.12,
)

# Showcase: denser near the knee (portfolio τ★ ≈ 0.28 with scheduled yaw is separate)
SHOWCASE_TIME_SCALES: tuple[float, ...] = (
    1.0,
    0.75,
    0.5,
    0.4,
    0.35,
    0.3,
    0.28,
    0.25,
    0.22,
    0.2,
    0.18,
    0.15,
    0.12,
)

# Portfolio dual-mission "envelope edge" operating point (time scale vs baseline F8)
ENVELOPE_EDGE_TIME_SCALE: float = 0.28

# Shared success bound so scheme curves are comparable (portfolio studies differ)
DEFAULT_ENVELOPE_POSITION_BOUND_M: float = 0.75


@dataclass(frozen=True)
class EnvelopeScheme:
    """One controller × sensor stack swept over τ."""

    id: str
    label: str
    family: str  # "lqr" | "pid"
    sensors: str
    study_rel: str
    method: str = ""

    def to_meta(self) -> dict[str, str]:
        return {
            "id": self.id,
            "label": self.label,
            "family": self.family,
            "sensors": self.sensors,
            "study": self.study_rel,
            "method": self.method,
        }


# Full teaching-matrix schemes (no Monte Carlo). Order matches gallery matrix.
MATRIX_SCHEMES: tuple[EnvelopeScheme, ...] = (
    EnvelopeScheme(
        id="ideal_lqr",
        label="Ideal LQR",
        family="lqr",
        sensors="x_true",
        study_rel="configs/studies/figure_eight.yaml",
        method="LQR",
    ),
    EnvelopeScheme(
        id="gps_imu_naive_lqr",
        label="GPS+IMU naive → LQR",
        family="lqr",
        sensors="pos+omega",
        study_rel="configs/studies/figure_eight_gps_imu_naive.yaml",
        method="partial_raw → LQR",
    ),
    EnvelopeScheme(
        id="gps_imu_lqg",
        label="GPS+IMU LQG",
        family="lqr",
        sensors="pos+omega",
        study_rel="configs/studies/figure_eight_gps_imu_lqg.yaml",
        method="linear_kf → LQR",
    ),
    EnvelopeScheme(
        id="ahrs_lqg",
        label="AHRS LQG",
        family="lqr",
        sensors="att+omega",
        study_rel="configs/studies/figure_eight_ahrs_lqg.yaml",
        method="linear_kf → LQR",
    ),
    EnvelopeScheme(
        id="flow_alt_lqg",
        label="Flow+alt LQG",
        family="lqr",
        sensors="body_vel+alt+omega",
        study_rel="configs/studies/figure_eight_flow_alt_lqg.yaml",
        method="linear_kf → LQR",
    ),
    EnvelopeScheme(
        id="imu_only_lqg",
        label="IMU-only LQG",
        family="lqr",
        sensors="omega",
        study_rel="configs/studies/figure_eight_imu_only_lqg.yaml",
        method="linear_kf → LQR",
    ),
    EnvelopeScheme(
        id="ideal_pid",
        label="Ideal PID",
        family="pid",
        sensors="x_true",
        study_rel="configs/studies/figure_eight_pid.yaml",
        method="PID cascade",
    ),
    EnvelopeScheme(
        id="gps_imu_naive_pid",
        label="GPS+IMU naive → PID",
        family="pid",
        sensors="pos+omega",
        study_rel="configs/studies/figure_eight_gps_imu_naive_pid.yaml",
        method="partial_raw → PID",
    ),
    EnvelopeScheme(
        id="gps_imu_kf_pid",
        label="GPS+IMU KF → PID",
        family="pid",
        sensors="pos+omega",
        study_rel="configs/studies/figure_eight_gps_imu_kf_pid.yaml",
        method="linear_kf → PID",
    ),
    EnvelopeScheme(
        id="ahrs_kf_pid",
        label="AHRS KF → PID",
        family="pid",
        sensors="att+omega",
        study_rel="configs/studies/figure_eight_ahrs_kf_pid.yaml",
        method="linear_kf → PID",
    ),
    EnvelopeScheme(
        id="flow_alt_kf_pid",
        label="Flow+alt KF → PID",
        family="pid",
        sensors="body_vel+alt+omega",
        study_rel="configs/studies/figure_eight_flow_alt_kf_pid.yaml",
        method="linear_kf → PID",
    ),
    EnvelopeScheme(
        id="imu_only_kf_pid",
        label="IMU-only KF → PID",
        family="pid",
        sensors="omega",
        study_rel="configs/studies/figure_eight_imu_only_kf_pid.yaml",
        method="linear_kf → PID",
    ),
)

# Backward-compat aliases used by older call sites / docs
LAWS: tuple[tuple[str, str], ...] = (
    ("lqr", "none"),
    ("lqg", "linear_kf"),
)

# Default = full matrix (PID + all sensor stacks)
DEFAULT_SCHEMES: tuple[EnvelopeScheme, ...] = MATRIX_SCHEMES

# Legacy short name map: law id "lqr" / "lqg" → scheme
_LEGACY_LAW_TO_SCHEME: dict[str, str] = {
    "lqr": "ideal_lqr",
    "lqg": "gps_imu_lqg",  # teaching LQG is GPS+IMU KF; full-state KF is not a matrix cell
}


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
    """Full-channel KF (legacy envelope LQG); portfolio GPS+IMU LQG uses pos+omega only."""
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
    position_bound_m: float = DEFAULT_ENVELOPE_POSITION_BOUND_M,
) -> dict[str, Any]:
    """Legacy builder: force LQR + observer type on a base study dict."""
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
    st.setdefault("controller", {})
    st["controller"]["type"] = st["controller"].get("type") or "lqr_hover"
    st["_envelope"] = {"law": law, "observer": observer_type}
    return st


def build_envelope_study_from_scheme(
    *,
    scheme_study: dict[str, Any],
    scheme: EnvelopeScheme,
    mission_file: str,
    study_id: str,
    position_bound_m: float = DEFAULT_ENVELOPE_POSITION_BOUND_M,
) -> dict[str, Any]:
    """Clone a portfolio study, point it at a scaled mission, unify success bound."""
    st = copy.deepcopy(scheme_study)
    st["study_id"] = study_id
    st.setdefault("guidance", {})
    st["guidance"]["mission_file"] = mission_file
    # Envelope uses constant-yaw time-scale stress (not scheduled-yaw edge mission)
    if "yaw_mode" not in st["guidance"]:
        st["guidance"]["yaw_mode"] = "constant"
    st.setdefault("metrics", {})
    st["metrics"]["position_bound_m"] = position_bound_m
    st.pop("monte_carlo", None)
    obs = ((st.get("sim") or {}).get("observer") or {}) if isinstance(st.get("sim"), dict) else {}
    st["_envelope"] = {
        "law": scheme.id,
        "family": scheme.family,
        "observer": obs.get("type", "none"),
        "controller": ((st.get("controller") or {}).get("type") or ""),
    }
    return st


def _resolve_schemes(
    schemes: Sequence[EnvelopeScheme] | None,
    laws: Sequence[tuple[str, str]] | None,
    scheme_ids: Sequence[str] | None,
) -> list[EnvelopeScheme]:
    if schemes is not None:
        return list(schemes)
    if scheme_ids is not None:
        by_id = {s.id: s for s in MATRIX_SCHEMES}
        out: list[EnvelopeScheme] = []
        for sid in scheme_ids:
            if sid not in by_id:
                msg = f"Unknown envelope scheme id {sid!r}; known: {sorted(by_id)}"
                raise KeyError(msg)
            out.append(by_id[sid])
        return out
    if laws is not None:
        # Legacy (law, observer) pairs → map known law names onto matrix schemes
        by_id = {s.id: s for s in MATRIX_SCHEMES}
        out = []
        for law, _obs in laws:
            mapped = _LEGACY_LAW_TO_SCHEME.get(law, law)
            if mapped in by_id:
                out.append(by_id[mapped])
            elif law == "lqr":
                out.append(by_id["ideal_lqr"])
            elif law in ("lqg", "pid"):
                # full-state LQG legacy or bare pid → closest matrix cells
                out.append(by_id["gps_imu_lqg"] if law == "lqg" else by_id["ideal_pid"])
            else:
                msg = f"Unknown legacy envelope law {law!r}"
                raise KeyError(msg)
        return out
    return list(DEFAULT_SCHEMES)


def run_linearization_envelope(
    *,
    repo_root: str | Path | None = None,
    base_study_path: str | Path = "configs/studies/figure_eight.yaml",
    base_mission_path: str | Path | None = None,
    time_scales: Sequence[float] | None = None,
    schemes: Sequence[EnvelopeScheme] | None = None,
    scheme_ids: Sequence[str] | None = None,
    laws: Sequence[tuple[str, str]] | None = None,
    output_root: str | Path | None = None,
    position_bound_m: float = DEFAULT_ENVELOPE_POSITION_BOUND_M,
) -> dict[str, Any]:
    """
    Sweep time-scaled figure-eight over controller × sensor schemes.

    Prefer ``schemes`` / ``scheme_ids`` (matrix cells). ``laws`` is a legacy
    (name, observer) API that maps onto a subset of matrix schemes.

    Returns a JSON-serializable envelope document with one point per (τ, scheme).
    """
    from uavsim.studies import run_nominal_study

    root = Path(repo_root or Path.cwd()).resolve()
    scheme_list = _resolve_schemes(schemes, laws, scheme_ids)

    # Default mission from ideal LQR study if not provided
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
    out = Path(output_root or (root / "runs" / "_envelope")).resolve()
    out.mkdir(parents=True, exist_ok=True)
    missions_dir = out / "missions"
    studies_dir = out / "studies"
    missions_dir.mkdir(exist_ok=True)
    studies_dir.mkdir(exist_ok=True)

    # Cache loaded portfolio studies
    study_cache: dict[str, dict[str, Any]] = {}
    for sch in scheme_list:
        sp = root / sch.study_rel
        if not sp.is_file():
            msg = f"Envelope scheme study missing: {sp}"
            raise FileNotFoundError(msg)
        with sp.open(encoding="utf-8") as f:
            study_cache[sch.id] = yaml.safe_load(f)

    points: list[dict[str, Any]] = []
    for tau in scales:
        miss = write_scaled_mission(mission_path, float(tau), missions_dir / f"tau_{tau:g}.yaml")
        for sch in scheme_list:
            sid = f"envelope_tau{tau:g}_{sch.id}"
            st = build_envelope_study_from_scheme(
                scheme_study=study_cache[sch.id],
                scheme=sch,
                mission_file=str(miss),
                study_id=sid,
                position_bound_m=position_bound_m,
            )
            st_write = {k: v for k, v in st.items() if not k.startswith("_")}
            sp = studies_dir / f"{sid}.yaml"
            with sp.open("w", encoding="utf-8") as f:
                yaml.safe_dump(st_write, f, sort_keys=False)
            result = run_nominal_study(sp, output_root=out, run_mc=False)
            m = dict(result.metrics or {})
            obs = ((st_write.get("sim") or {}).get("observer") or {}) if st_write.get("sim") else {}
            ctrl = (st_write.get("controller") or {}).get("type")
            points.append(
                {
                    "time_scale": float(tau),
                    "aggressiveness": float(1.0 / tau) if tau else None,
                    "law": sch.id,  # stable series key (was "lqr"/"lqg")
                    "label": sch.label,
                    "family": sch.family,
                    "sensors": sch.sensors,
                    "method": sch.method,
                    "controller": ctrl,
                    "observer": obs.get("type", "none"),
                    "observer_channels": obs.get("channels"),
                    "study_id": sid,
                    "source_study": sch.study_rel,
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

    # Walk gentle (large τ) → aggressive (small τ); last success / first fail per scheme
    boundary: dict[str, Any] = {}
    for sch in scheme_list:
        law_pts = sorted(
            [p for p in points if p["law"] == sch.id],
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
        boundary[sch.id] = {
            "label": sch.label,
            "family": sch.family,
            "last_success_time_scale": last_ok["time_scale"] if last_ok else None,
            "first_fail_time_scale": first_fail["time_scale"] if first_fail else None,
            "last_success_peak_tilt_deg": last_ok.get("peak_tilt_deg") if last_ok else None,
            "first_fail_peak_tilt_deg": first_fail.get("peak_tilt_deg") if first_fail else None,
        }

    return {
        "schema_version": 2,
        "kind": "linearization_envelope",
        "title": "Controller × sensor tracking envelope",
        "description": (
            "Figure-eight mission time scale τ (1 = portfolio baseline path). "
            "Smaller τ shortens segments → higher speed/tilt demand. "
            "Each series is a portfolio matrix cell (cascade PID and hover LQR × "
            "ideal / GPS+IMU naive / GPS+IMU KF / AHRS / flow+alt / IMU-only). "
            "Success uses a shared position bound so curves are comparable. "
            "Breakdown marks where that stack leaves a usable tracking region — "
            "not only the classical hover-LQR linearization story."
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
        "schemes": [s.to_meta() for s in scheme_list],
        # laws: UI / older readers — list of series ids with observer hint
        "laws": [
            {
                "id": s.id,
                "label": s.label,
                "family": s.family,
                "observer": (
                    ((study_cache[s.id].get("sim") or {}).get("observer") or {}).get("type")
                    or "none"
                ),
            }
            for s in scheme_list
        ],
        "position_bound_m": position_bound_m,
        "points": points,
        "boundary": boundary,
        "showcase_edge_time_scale": ENVELOPE_EDGE_TIME_SCALE,
        "notes": [
            "τ-axis is pure time compression on the constant-yaw figure-eight "
            "(same geometry as the baseline matrix mission).",
            "LQR schemes use hover A,B linearization; PID cascade uses the "
            "portfolio gains (not redesigned per τ).",
            "KF schemes share the hover linear process model — mismatch grows "
            "with aggression and with missing sensors.",
            "Naive partial_raw leaves zeros for unobserved states — expect early "
            "failure independent of linearization tilt.",
            "IMU-only / AHRS lack absolute horizontal position — often fail the "
            "shared bound at τ=1 already; still useful honesty curves.",
            (
                "Portfolio envelope-edge mission (scheduled yaw) sits near "
                f"τ★≈{ENVELOPE_EDGE_TIME_SCALE:g} on this axis but adds yaw demand."
            ),
        ],
    }
