"""Closed-loop stack provenance for showcase gallery entries.

Assembles ``runs[i].stack`` from study_config, controller artifact, vehicle,
and mission YAML per ``docs/showcase/STACK_SPEC.md``.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

STACK_SCHEMA_VERSION = 1
TOPOLOGY_ID = "closed_loop_sil"

DEFAULT_EDGES: list[list[str]] = [
    ["mission", "guidance"],
    ["guidance", "controller"],
    ["sensors", "observer"],
    ["observer", "controller"],
    ["controller", "actuators"],
    ["actuators", "plant"],
    ["plant", "sensors"],
    ["plant", "metrics"],
]

_NODE_ORDER = (
    "mission",
    "guidance",
    "sensors",
    "observer",
    "controller",
    "actuators",
    "plant",
    "metrics",
)


def build_stack_from_run_dir(
    run_dir: Path | str,
    *,
    gallery_id: str | None = None,
) -> dict[str, Any]:
    """Assemble stack from study_config + controller_artifact + vehicle + mission."""
    run_dir = Path(run_dir)
    study = _load_yaml(run_dir / "study_config.yaml") or {}
    manifest = _load_yaml(run_dir / "manifest.yaml") or {}
    artifact = _load_yaml(run_dir / "nominal" / "controller_artifact.yaml")
    metrics = _load_json(run_dir / "nominal" / "metrics.json")

    vehicle = _resolve_vehicle(study, artifact, run_dir)
    mission = _resolve_mission(study, run_dir)

    return build_stack_from_study_mapping(
        study,
        vehicle=vehicle,
        mission=mission,
        controller_artifact=artifact,
        manifest=manifest,
        metrics=metrics,
        gallery_id=gallery_id,
        source_run=run_dir.name,
        repo_root=_find_repo_root(run_dir),
    )


def build_stack_from_study_mapping(
    study: dict[str, Any],
    *,
    vehicle: dict[str, Any] | None = None,
    mission: dict[str, Any] | None = None,
    controller_artifact: dict[str, Any] | None = None,
    manifest: dict[str, Any] | None = None,
    metrics: dict[str, Any] | None = None,
    gallery_id: str | None = None,
    source_run: str | None = None,
    repo_root: Path | None = None,
    mission_file: str | None = None,
    vehicle_path: str | None = None,
) -> dict[str, Any]:
    """Config-only path for tests / offline enrich without timeseries."""
    study = study or {}
    manifest = manifest or {}
    repo_root = repo_root or _find_repo_root(Path.cwd())

    if vehicle is None:
        vehicle = _load_vehicle_from_study(study, repo_root)
    if mission is None:
        mission = _load_mission_from_study(study, repo_root)

    guidance = dict(study.get("guidance") or {})
    sim = dict(study.get("sim") or {})
    observer_cfg = dict(sim.get("observer") or {})
    controller_cfg = dict(study.get("controller") or {})
    metrics_cfg = dict(study.get("metrics") or {})

    # Paths for identity / mission details
    m_file = mission_file or guidance.get("mission_file")
    v_path = vehicle_path or study.get("vehicle")
    m_file_rel = _relativize_config_path(m_file, repo_root)
    v_path_rel = _relativize_config_path(v_path, repo_root)

    details_mission = _details_mission(mission, guidance, m_file_rel)
    details_guidance = _details_guidance(guidance, m_file_rel)
    details_sensors, details_observer = _details_sensors_observer(observer_cfg)
    details_controller = _details_controller(controller_cfg, controller_artifact)
    details_actuators = _details_actuators(sim, vehicle)
    details_plant = _details_plant(sim, vehicle)
    details_metrics = _details_metrics(metrics_cfg, metrics)
    details_identity = _details_identity(
        study=study,
        manifest=manifest,
        vehicle=vehicle,
        gallery_id=gallery_id,
        source_run=source_run,
        vehicle_path=v_path_rel,
    )

    details: dict[str, Any] = {
        "mission": details_mission,
        "guidance": details_guidance,
        "sensors": details_sensors,
        "observer": details_observer,
        "controller": details_controller,
        "actuators": details_actuators,
        "plant": details_plant,
        "metrics": details_metrics,
        "identity": details_identity,
    }

    nodes = [
        _node_mission(details_mission),
        _node_guidance(details_guidance),
        _node_sensors(details_sensors, details_observer),
        _node_observer(details_observer),
        _node_controller(details_controller),
        _node_actuators(details_actuators),
        _node_plant(details_plant),
        _node_metrics(details_metrics),
    ]

    return {
        "schema_version": STACK_SCHEMA_VERSION,
        "topology": TOPOLOGY_ID,
        "nodes": nodes,
        "edges": [list(e) for e in DEFAULT_EDGES],
        "details": details,
    }


# ---------------------------------------------------------------------------
# Details builders
# ---------------------------------------------------------------------------


def _details_identity(
    *,
    study: dict[str, Any],
    manifest: dict[str, Any],
    vehicle: dict[str, Any] | None,
    gallery_id: str | None,
    source_run: str | None,
    vehicle_path: str | None,
) -> dict[str, Any]:
    code = manifest.get("code_identity") or {}
    vehicle_id = None
    if vehicle:
        vehicle_id = vehicle.get("vehicle_id")
    vehicle_id = vehicle_id or manifest.get("vehicle_id") or study.get("vehicle_id")
    return {
        "study_id": study.get("study_id") or manifest.get("study_id"),
        "gallery_id": gallery_id,
        "seed": study.get("seed", manifest.get("seed")),
        "git_commit": code.get("git_commit") if isinstance(code, dict) else None,
        "config_hash": manifest.get("config_hash"),
        "uavsim_version": manifest.get("uavsim_version") or (vehicle or {}).get("uavsim_version"),
        "vehicle_id": vehicle_id,
        "vehicle_path": vehicle_path,
        "source_run": source_run,
    }


def _details_mission(
    mission: dict[str, Any] | None,
    guidance: dict[str, Any],
    mission_file: str | None,
) -> dict[str, Any]:
    mission = mission or {}
    wps = mission.get("waypoints") or []
    n_wp = len(wps) if isinstance(wps, list) else 0
    duration_s = None
    preview: list[dict[str, Any]] = []
    if isinstance(wps, list) and wps:
        times = [float(w.get("time", 0.0)) for w in wps if isinstance(w, dict)]
        if times:
            duration_s = max(times) - min(times)
        for w in wps[:9]:
            if not isinstance(w, dict):
                continue
            preview.append(
                {
                    "t": w.get("time"),
                    "x": w.get("x"),
                    "y": w.get("y"),
                    "z": w.get("z"),
                    "yaw": w.get("yaw"),
                    **({"label": w["label"]} if w.get("label") is not None else {}),
                }
            )
    return {
        "mission_file": mission_file,
        "name": mission.get("name"),
        "frame": mission.get("frame"),
        "n_waypoints": n_wp,
        "duration_s": duration_s,
        "yaw_mode": guidance.get("yaw_mode"),
        "waypoints_preview": preview or None,
    }


def _details_guidance(guidance: dict[str, Any], mission_file: str | None) -> dict[str, Any]:
    return {
        "type": guidance.get("type"),
        "method": guidance.get("method"),
        "yaw_mode": guidance.get("yaw_mode"),
        "sample_dt_s": guidance.get("sample_dt_s"),
        "fail_on_infeasible": guidance.get("fail_on_infeasible"),
        "mission_file": mission_file or _as_str_or_none(guidance.get("mission_file")),
    }


def _details_sensors_observer(
    observer_cfg: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    obs_type = observer_cfg.get("type") or "none"
    channels = observer_cfg.get("channels")
    shared = {
        "observer_type": obs_type,
        "channels": channels,
        "pos_sigma_m": observer_cfg.get("pos_sigma_m"),
        "vel_sigma_m_s": observer_cfg.get("vel_sigma_m_s"),
        "att_sigma_rad": observer_cfg.get("att_sigma_rad"),
        "omega_sigma_rad_s": observer_cfg.get("omega_sigma_rad_s"),
        "process_sigma": observer_cfg.get("process_sigma"),
        "seed": observer_cfg.get("seed"),
    }
    notes = None
    if obs_type in (None, "none"):
        notes = "identity (true state); full-state feedback"
    elif obs_type == "partial_raw":
        notes = "naive partial sensors; unobserved states zeroed on control bus"
    elif obs_type in ("linear_kf", "kf"):
        notes = "linear Kalman filter reconstructs full state from channels"
    shared_obs = {**shared, "notes": notes}
    # sensors share noise/channel fields; observer emphasizes type/notes
    sensors = {
        "observer_type": obs_type,
        "channels": channels,
        "pos_sigma_m": shared["pos_sigma_m"],
        "vel_sigma_m_s": shared["vel_sigma_m_s"],
        "att_sigma_rad": shared["att_sigma_rad"],
        "omega_sigma_rad_s": shared["omega_sigma_rad_s"],
        "process_sigma": shared["process_sigma"],
        "seed": shared["seed"],
        "notes": notes,
    }
    return sensors, shared_obs


def _details_controller(
    controller_cfg: dict[str, Any],
    artifact: dict[str, Any] | None,
) -> dict[str, Any]:
    art = artifact or {}
    ctype = art.get("controller_type") or controller_cfg.get("type") or art.get("controller_id")
    gains_src = art.get("gains") if isinstance(art.get("gains"), dict) else None
    if gains_src is None:
        gains_src = _gains_from_controller_cfg(controller_cfg, ctype)

    trim = art.get("trim") if isinstance(art.get("trim"), dict) else {}
    u_hover = trim.get("u_hover")
    if u_hover is None and "u_hover" in controller_cfg:
        u_hover = controller_cfg.get("u_hover")

    equation = _controller_equation(str(ctype) if ctype else None)
    design = art.get("design") if isinstance(art.get("design"), dict) else None
    vehicle_trim = None
    if isinstance(art.get("vehicle"), dict):
        v = art["vehicle"]
        vehicle_trim = {
            "mass_kg": v.get("mass_kg"),
            "arm_length_m": v.get("arm_length_m"),
            "inertia": v.get("inertia"),
            "limits": v.get("limits"),
        }

    out: dict[str, Any] = {
        "type": ctype,
        "frames": art.get("frames"),
        "u_hover": u_hover,
        "gains": gains_src,
        "design": design,
        "vehicle_trim": vehicle_trim,
        "equation": equation,
    }
    return out


def _gains_from_controller_cfg(cfg: dict[str, Any], ctype: Any) -> dict[str, Any] | None:
    if not cfg:
        return None
    t = str(ctype or cfg.get("type") or "")
    if t == "lqr_hover" or "Q_diag" in cfg:
        g: dict[str, Any] = {}
        if "Q_diag" in cfg:
            g["Q_diag"] = cfg["Q_diag"]
        if "R_diag" in cfg:
            g["R_diag"] = cfg["R_diag"]
        if "K" in cfg:
            g["K"] = cfg["K"]
        return g or None
    if t == "pid_cascade" or any(k.startswith("kp_") for k in cfg):
        keys = (
            "kp_pos",
            "kd_pos",
            "kp_att",
            "kd_rate",
            "max_tilt_rad",
        )
        g = {k: cfg[k] for k in keys if k in cfg}
        return g or None
    # generic: strip type
    return {k: v for k, v in cfg.items() if k != "type"} or None


def _controller_equation(ctype: str | None) -> str | None:
    if not ctype:
        return None
    if ctype == "lqr_hover":
        return "u = u_h − K(x̂ − x_r)"
    if ctype == "pid_cascade":
        return "cascade PID (pos→att→rate) → body wrench"
    return None


def _details_actuators(sim: dict[str, Any], vehicle: dict[str, Any] | None) -> dict[str, Any]:
    plant_mode = sim.get("plant") or "wrench"
    vehicle = vehicle or {}
    prop = vehicle.get("propulsion") if isinstance(vehicle.get("propulsion"), dict) else {}
    lim = vehicle.get("limits") if isinstance(vehicle.get("limits"), dict) else {}
    mixer = None
    if prop:
        mixer = {
            "layout": prop.get("layout"),
            "ct_n_s2": prop.get("ct_n_s2"),
            "cq_nm_s2": prop.get("cq_nm_s2"),
        }
    return {
        "plant_mode": plant_mode,
        "command": "body_wrench",
        "mixer": mixer,
        "motor_time_const_s": prop.get("motor_time_const_s"),
        "omega_min_rad_s": prop.get("omega_min_rad_s"),
        "omega_max_rad_s": prop.get("omega_max_rad_s"),
        "limits": {
            "thrust_min_n": lim.get("thrust_min_n"),
            "thrust_max_n": lim.get("thrust_max_n"),
            "torque_max_nm": lim.get("torque_max_nm"),
        }
        if lim
        else None,
    }


def _details_plant(sim: dict[str, Any], vehicle: dict[str, Any] | None) -> dict[str, Any]:
    plant_mode = sim.get("plant") or "wrench"
    attitude = sim.get("attitude") or "euler"
    vehicle = vehicle or {}
    aero = vehicle.get("aero") if isinstance(vehicle.get("aero"), dict) else None
    aero_out = None
    notes = None
    if aero:
        enabled = any(
            float(aero.get(k) or 0.0) != 0.0
            for k in (
                "drag_lin_ns_m",
                "drag_quad_ns2_m2",
                "rate_damp_nm_s",
                "prop_h_s_per_m",
            )
        ) or (aero.get("ground_effect") not in (None, "none", False))
        aero_out = {**aero, "enabled": bool(enabled)}
        if not enabled:
            notes = "Aero defaults off (vacuum plant)"
    else:
        notes = "Aero defaults off (vacuum plant)"

    v_snap = {
        "mass_kg": vehicle.get("mass_kg"),
        "gravity_m_s2": vehicle.get("gravity_m_s2"),
        "arm_length_m": vehicle.get("arm_length_m"),
        "inertia": vehicle.get("inertia"),
        "limits": vehicle.get("limits"),
    }
    return {
        "attitude": attitude,
        "plant_mode": plant_mode,
        "state_dim_bus": 12,
        "dynamics": "rigid_body_6dof",
        "vehicle": v_snap,
        "aero": aero_out,
        "integrator": {
            "dt_s": sim.get("dt_s"),
            "method": sim.get("method"),
            "rtol": sim.get("rtol"),
            "atol": sim.get("atol"),
        },
        "notes": notes,
    }


def _details_metrics(
    metrics_cfg: dict[str, Any],
    reported: dict[str, Any] | None,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "position_bound_m": metrics_cfg.get("position_bound_m"),
        "reported": None,
    }
    if reported:
        keys = (
            "rmse_position_m",
            "rmse_attitude_rad",
            "within_bound",
            "success",
            "time_in_bounds_frac",
            "peak_position_error_m",
        )
        subset = {k: reported[k] for k in keys if k in reported}
        out["reported"] = subset or None
    return out


# ---------------------------------------------------------------------------
# Node summaries
# ---------------------------------------------------------------------------


def _node(nid: str, title: str, summary: str, badges: list[str] | None = None) -> dict[str, Any]:
    n: dict[str, Any] = {
        "id": nid,
        "kind": nid,
        "title": title,
        "summary": summary,
    }
    if badges:
        n["badges"] = badges
    return n


def _node_mission(d: dict[str, Any]) -> dict[str, Any]:
    name = d.get("name") or "Mission"
    n = d.get("n_waypoints")
    dur = d.get("duration_s")
    parts = []
    if n is not None:
        parts.append(f"{n} waypoints")
    if dur is not None:
        parts.append(f"{dur:.0f}s")
    summary = ", ".join(parts) if parts else (d.get("frame") or "trajectory")
    return _node("mission", str(name).replace("_", " ").title(), summary)


def _node_guidance(d: dict[str, Any]) -> dict[str, Any]:
    gtype = d.get("type") or "guidance"
    method = d.get("method")
    yaw = d.get("yaw_mode")
    bits = [b for b in (method, yaw) if b]
    summary = " · ".join(str(b) for b in bits) if bits else str(gtype)
    return _node("guidance", "Guidance", summary, badges=[str(gtype)] if gtype else None)


def _node_sensors(d_s: dict[str, Any], d_o: dict[str, Any]) -> dict[str, Any]:
    ch = d_s.get("channels")
    obs = d_o.get("observer_type") or "none"
    if obs in (None, "none"):
        summary = "full state (no noise)"
        badges = ["ideal"]
    elif ch:
        summary = "+".join(str(c) for c in ch)
        badges = list(ch) if isinstance(ch, list) else [str(ch)]
    else:
        summary = "sensors"
        badges = None
    return _node("sensors", "Sensors", summary, badges=badges)


def _node_observer(d: dict[str, Any]) -> dict[str, Any]:
    obs = d.get("observer_type") or "none"
    if obs in (None, "none"):
        summary = "identity (true state)"
        title = "Observer"
        badges = ["none"]
    elif obs == "partial_raw":
        summary = "naive partial → zeros unobserved"
        title = "Observer"
        badges = ["partial_raw"]
        ch = d.get("channels")
        if isinstance(ch, list):
            badges = ["partial_raw", *[str(c) for c in ch]]
    else:
        summary = str(obs).replace("_", " ")
        title = "Observer"
        badges = [str(obs)]
        ch = d.get("channels")
        if isinstance(ch, list):
            badges = [str(obs), *[str(c) for c in ch]]
    return _node("observer", title, summary, badges=badges)


def _node_controller(d: dict[str, Any]) -> dict[str, Any]:
    ctype = d.get("type") or "controller"
    titles = {
        "lqr_hover": "Hover LQR",
        "pid_cascade": "PID cascade",
    }
    title = titles.get(str(ctype), str(ctype).replace("_", " "))
    summary = d.get("equation") or str(ctype)
    return _node("controller", title, summary, badges=[str(ctype)])


def _node_actuators(d: dict[str, Any]) -> dict[str, Any]:
    mode = d.get("plant_mode") or "wrench"
    summary = "mixer + 1st-order motors" if mode == "motors" else "body wrench command"
    return _node("actuators", "Actuators", summary, badges=[str(mode)])


def _node_plant(d: dict[str, Any]) -> dict[str, Any]:
    att = d.get("attitude") or "euler"
    mode = d.get("plant_mode") or "wrench"
    summary = f"6-DoF rigid body · {att}"
    return _node("plant", "Plant", summary, badges=[str(mode), str(att)])


def _node_metrics(d: dict[str, Any]) -> dict[str, Any]:
    bound = d.get("position_bound_m")
    summary = f"|e|_pos ≤ {bound} m" if bound is not None else "tracking bounds"
    return _node("metrics", "Metrics", summary)


# ---------------------------------------------------------------------------
# Path / YAML helpers
# ---------------------------------------------------------------------------


def _load_yaml(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        with path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data if isinstance(data, dict) else None
    except Exception as exc:  # noqa: BLE001 — degrade gracefully
        logger.debug("stack: failed to load YAML %s: %s", path, exc)
        return None


def _load_json(path: Path) -> dict[str, Any] | None:
    import json

    if not path.is_file():
        return None
    try:
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else None
    except Exception as exc:  # noqa: BLE001
        logger.debug("stack: failed to load JSON %s: %s", path, exc)
        return None


def _find_repo_root(start: Path) -> Path | None:
    """Walk up looking for configs/ + (pyproject.toml or .git)."""
    cur = start.resolve()
    if cur.is_file():
        cur = cur.parent
    for _ in range(12):
        if (cur / "configs").is_dir() and (
            (cur / "pyproject.toml").is_file() or (cur / ".git").exists()
        ):
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    # fallback: cwd
    cwd = Path.cwd()
    if (cwd / "configs").is_dir():
        return cwd
    return None


def _relativize_config_path(path: str | Path | None, repo_root: Path | None) -> str | None:
    if path is None:
        return None
    s = str(path)
    if not s:
        return None
    # Already relative configs/...
    norm = s.replace("\\", "/")
    if "configs/" in norm:
        idx = norm.find("configs/")
        return norm[idx:]
    p = Path(s)
    if repo_root is not None:
        try:
            rel = p.resolve().relative_to(repo_root.resolve())
            return str(rel).replace("\\", "/")
        except (ValueError, OSError):
            pass
    return s


def _as_str_or_none(v: Any) -> str | None:
    if v is None:
        return None
    return str(v)


def _resolve_path(
    raw: str | Path | None,
    repo_root: Path | None,
    base: Path | None = None,
) -> Path | None:
    if raw is None:
        return None
    p = Path(str(raw))
    if p.is_file():
        return p
    candidates: list[Path] = []
    if repo_root is not None:
        candidates.append(repo_root / p)
    if base is not None:
        candidates.append(base / p)
    candidates.append(Path.cwd() / p)
    for c in candidates:
        if c.is_file():
            return c
    return None


def _load_vehicle_from_study(
    study: dict[str, Any], repo_root: Path | None
) -> dict[str, Any] | None:
    return _load_yaml(_resolve_path(study.get("vehicle"), repo_root) or Path("__missing__"))


def _load_mission_from_study(
    study: dict[str, Any], repo_root: Path | None
) -> dict[str, Any] | None:
    guidance = study.get("guidance") or {}
    return _load_yaml(_resolve_path(guidance.get("mission_file"), repo_root) or Path("__missing__"))


def _resolve_vehicle(
    study: dict[str, Any],
    artifact: dict[str, Any] | None,
    run_dir: Path,
) -> dict[str, Any] | None:
    repo_root = _find_repo_root(run_dir)
    v = _load_vehicle_from_study(study, repo_root)
    if v is not None:
        return v
    # artifact vehicle snapshot is partial (no propulsion/aero often)
    if artifact and isinstance(artifact.get("vehicle"), dict):
        snap = dict(artifact["vehicle"])
        if artifact.get("vehicle_id"):
            snap.setdefault("vehicle_id", artifact["vehicle_id"])
        return snap
    return None


def _resolve_mission(study: dict[str, Any], run_dir: Path) -> dict[str, Any] | None:
    repo_root = _find_repo_root(run_dir)
    return _load_mission_from_study(study, repo_root)
