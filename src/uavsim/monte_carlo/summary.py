"""Aggregate Monte Carlo trial tables into summary statistics."""

from __future__ import annotations

from typing import Any

import numpy as np

METRIC_KEYS = (
    "rmse_position_m",
    "max_position_error_m",
    "final_position_error_m",
    "time_in_bounds_frac",
    "rmse_attitude_rad",
    "max_attitude_error_rad",
    "rmse_velocity_m_s",
    "control_effort_proxy",
    "peak_thrust_n",
    "peak_torque_nm",
)

PARAM_KEYS = (
    "mass_kg",
    "ixx_kg_m2",
    "iyy_kg_m2",
    "izz_kg_m2",
    "arm_length_m",
    "ct_n_s2",
    "cq_nm_s2",
    "motor_time_const_s",
    "omega_max_rad_s",
)


def _safe_float(row: dict[str, Any], key: str) -> float | None:
    val = row.get(key)
    if val is None:
        return None
    try:
        f = float(val)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(f):
        return None
    return f


def _metric_block(
    trials: list[dict[str, Any]], keys: tuple[str, ...] = METRIC_KEYS
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key in keys:
        vals = np.array(
            [v for t in trials if (v := _safe_float(t, key)) is not None],
            dtype=float,
        )
        if vals.size == 0:
            continue
        out[key] = {
            "mean": float(np.mean(vals)),
            "std": float(np.std(vals, ddof=0)),
            "min": float(np.min(vals)),
            "max": float(np.max(vals)),
            "p50": float(np.percentile(vals, 50)),
            "p95": float(np.percentile(vals, 95)),
            "n": int(vals.size),
        }
    return out


def _correlations_vs_rmse(trials: list[dict[str, Any]]) -> dict[str, float | None]:
    corr: dict[str, float | None] = {}
    rmse = np.array([_safe_float(t, "rmse_position_m") for t in trials], dtype=float)
    for pkey in PARAM_KEYS:
        p = np.array([_safe_float(t, pkey) for t in trials], dtype=float)
        mask = np.isfinite(rmse) & np.isfinite(p)
        if int(np.sum(mask)) < 3:
            corr[pkey] = None
            continue
        if float(np.std(rmse[mask])) < 1e-15 or float(np.std(p[mask])) < 1e-15:
            corr[pkey] = None
            continue
        corr[pkey] = float(np.corrcoef(p[mask], rmse[mask])[0, 1])
    return corr


def summarize_trials(trials: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Build schema-versioned summary from trial row dicts.

    **Primary tracking stats** (``metrics``) use **successful trials only** so a
    few divergences do not dominate mean/p95. Full-population stats (including
    failures) are under ``metrics_all_trials``.
    """
    n = len(trials)
    if n == 0:
        return {
            "schema_version": 2,
            "n_trials": 0,
            "n_success": 0,
            "n_sim_success": 0,
            "failure_rate": None,
            "metrics": {},
            "metrics_all_trials": {},
            "metrics_population": "success_only",
            "correlations_vs_rmse_position": {},
        }

    success_flags = [bool(t.get("success", False)) for t in trials]
    sim_flags = [bool(t.get("sim_success", False)) for t in trials]
    n_success = int(sum(success_flags))
    n_sim = int(sum(sim_flags))
    success_trials = [t for t, ok in zip(trials, success_flags, strict=True) if ok]

    metrics_success = _metric_block(success_trials)
    metrics_all = _metric_block(trials)

    return {
        "schema_version": 2,
        "n_trials": n,
        "n_success": n_success,
        "n_sim_success": n_sim,
        "failure_rate": float(1.0 - n_success / n) if n else None,
        "sim_failure_rate": float(1.0 - n_sim / n) if n else None,
        # Primary: quality among trials that met success criteria
        "metrics": metrics_success,
        "metrics_population": "success_only",
        # Secondary: all finite metric values (blow-ups skew mean/p95)
        "metrics_all_trials": metrics_all,
        "correlations_vs_rmse_position": _correlations_vs_rmse(success_trials),
        "correlations_vs_rmse_position_all": _correlations_vs_rmse(trials),
    }
