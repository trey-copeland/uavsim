"""Load run-directory artifacts for viz consumers."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from uavsim.monte_carlo.io import read_trials_csv


@dataclass
class ActuatorLimitView:
    thrust_min_n: float = 0.0
    thrust_max_n: float = np.inf
    torque_max_nm: float = np.inf


@dataclass
class RunArtifacts:
    run_dir: Path
    study_id: str
    t: np.ndarray | None = None
    x: np.ndarray | None = None
    u: np.ndarray | None = None
    t_ref: np.ndarray | None = None
    x_ref: np.ndarray | None = None
    metrics: dict[str, Any] = field(default_factory=dict)
    feasibility: dict[str, Any] | None = None
    mc_summary: dict[str, Any] | None = None
    trials: list[dict[str, Any]] = field(default_factory=list)
    limits: ActuatorLimitView = field(default_factory=ActuatorLimitView)
    manifest: dict[str, Any] | None = None


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, dict) else None


def _load_yaml(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else None


def load_run(run_dir: str | Path) -> RunArtifacts:
    """Load nominal timeseries, optional reference grid, metrics, feasibility, MC."""
    run_dir = Path(run_dir)
    if not run_dir.is_dir():
        msg = f"Run directory not found: {run_dir}"
        raise FileNotFoundError(msg)

    manifest = _load_yaml(run_dir / "manifest.yaml")
    study_id = str((manifest or {}).get("study_id") or run_dir.name)

    t = x = u = None
    ts = run_dir / "nominal" / "timeseries.npz"
    if ts.is_file():
        data = np.load(ts)
        t = np.asarray(data["t"], dtype=float)
        x = np.asarray(data["x"], dtype=float)
        u = np.asarray(data["u"], dtype=float)

    t_ref = x_ref = None
    grid = run_dir / "reference" / "grid.npz"
    if grid.is_file():
        g = np.load(grid)
        t_ref = np.asarray(g["t"], dtype=float)
        x_ref = np.asarray(g["x"], dtype=float)

    metrics = _load_json(run_dir / "nominal" / "metrics.json") or {}
    feasibility = _load_json(run_dir / "guidance" / "feasibility.json")
    mc_summary = _load_json(run_dir / "monte_carlo" / "summary.json")
    trials_path = run_dir / "monte_carlo" / "trials.csv"
    trials = read_trials_csv(trials_path) if trials_path.is_file() else []

    limits = _resolve_limits(run_dir)

    return RunArtifacts(
        run_dir=run_dir,
        study_id=study_id,
        t=t,
        x=x,
        u=u,
        t_ref=t_ref,
        x_ref=x_ref,
        metrics=metrics,
        feasibility=feasibility,
        mc_summary=mc_summary,
        trials=trials,
        limits=limits,
        manifest=manifest,
    )


def _resolve_limits(run_dir: Path) -> ActuatorLimitView:
    """Prefer controller artifact vehicle limits; fall back to study vehicle file."""
    art = _load_yaml(run_dir / "nominal" / "controller_artifact.yaml")
    if art and isinstance(art.get("vehicle"), dict):
        lim = art["vehicle"].get("limits") or {}
        return ActuatorLimitView(
            thrust_min_n=float(lim.get("thrust_min_n", 0.0)),
            thrust_max_n=float(lim.get("thrust_max_n", np.inf)),
            torque_max_nm=float(lim.get("torque_max_nm", np.inf)),
        )

    study = _load_yaml(run_dir / "study_config.yaml")
    if study and study.get("vehicle"):
        vpath = Path(str(study["vehicle"]))
        if not vpath.is_file():
            # try relative to CWD
            vpath = Path.cwd() / vpath
        if vpath.is_file():
            v = _load_yaml(vpath)
            if v and isinstance(v.get("limits"), dict):
                lim = v["limits"]
                return ActuatorLimitView(
                    thrust_min_n=float(lim.get("thrust_min_n", 0.0)),
                    thrust_max_n=float(lim.get("thrust_max_n", np.inf)),
                    torque_max_nm=float(lim.get("torque_max_nm", np.inf)),
                )
    return ActuatorLimitView()


def ned_to_plot(pos_ned: np.ndarray) -> np.ndarray:
    """Map NED position(s) to plot coords (N, E, up=-D)."""
    p = np.asarray(pos_ned, dtype=float)
    if p.ndim == 1:
        return np.array([p[0], p[1], -p[2]], dtype=float)
    out = p.copy()
    out[:, 2] = -p[:, 2]
    return out


def body_axes_ned(euler: np.ndarray) -> np.ndarray:
    """Return 3×3 matrix with columns = body x,y,z expressed in NED."""
    from uavsim.dynamics.rotations import rotation_body_to_inertial

    phi, theta, psi = float(euler[0]), float(euler[1]), float(euler[2])
    return rotation_body_to_inertial(phi, theta, psi)


def interpolate_ref_at(t_ref: np.ndarray, x_ref: np.ndarray, t: float) -> np.ndarray:
    """Linear interpolate full state reference at time t."""
    t = float(np.clip(t, t_ref[0], t_ref[-1]))
    out = np.zeros(x_ref.shape[1], dtype=float)
    for j in range(x_ref.shape[1]):
        out[j] = float(np.interp(t, t_ref, x_ref[:, j]))
    return out


def saturation_mask(
    u: np.ndarray, limits: ActuatorLimitView, *, margin: float = 0.98
) -> np.ndarray:
    """Boolean (N,) true when thrust or any torque is within margin of limits."""
    u = np.asarray(u, dtype=float)
    if u.ndim != 2 or u.shape[1] < 4:
        return np.zeros(u.shape[0], dtype=bool)
    f = u[:, 0]
    tau = np.abs(u[:, 1:4])
    f_hi = np.isfinite(limits.thrust_max_n) and limits.thrust_max_n > 0
    t_hi = np.isfinite(limits.torque_max_nm) and limits.torque_max_nm > 0
    sat = np.zeros(u.shape[0], dtype=bool)
    if f_hi:
        sat |= f >= margin * limits.thrust_max_n
        if limits.thrust_min_n > 0:
            sat |= f <= limits.thrust_min_n + (1 - margin) * (
                limits.thrust_max_n - limits.thrust_min_n
            )
    if t_hi:
        sat |= np.any(tau >= margin * limits.torque_max_nm, axis=1)
    return sat
