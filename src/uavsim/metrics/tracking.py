"""Tracking and control metrics."""

from __future__ import annotations

from typing import Any

import numpy as np

from uavsim.dynamics.attitude_error import (
    geodesic_attitude_error_rad,
    rotation_error_vector_from_euler,
)
from uavsim.reference import ReferenceTrajectory


def compute_metrics(
    t: np.ndarray,
    x: np.ndarray,
    u: np.ndarray,
    reference: ReferenceTrajectory,
    *,
    position_bound_m: float = 0.1,
    x_ref: np.ndarray | None = None,
) -> dict[str, Any]:
    """Tracking metrics vs the reference the controller was given.

    Prefer ``x_ref`` when provided: the per-sample commanded state actually used
    at each control tick. Re-evaluating a single ``ReferenceTrajectory`` object
    after the run is wrong for online replan (``intercept_pursue``), where
    ``adapter.reference`` is only the *last* segment and ``evaluate`` clamps
    out-of-range times to that segment's ``t0`` — producing garbage RMSE.
    """
    if x_ref is None:
        x_ref_arr = np.vstack([reference.evaluate(float(ti)).x_ref for ti in t])
    else:
        x_ref_arr = np.asarray(x_ref, dtype=float)
        if x_ref_arr.shape != np.asarray(x, dtype=float).shape:
            msg = (
                f"x_ref shape {x_ref_arr.shape} must match state trajectory shape "
                f"{np.asarray(x).shape}"
            )
            raise ValueError(msg)
    e_pos = x[:, 0:3] - x_ref_arr[:, 0:3]
    e_vel = x[:, 6:9] - x_ref_arr[:, 6:9]

    # SO(3) attitude error (geodesic angle + rotation-vector components)
    e_att_vec = np.vstack(
        [rotation_error_vector_from_euler(x[i, 3:6], x_ref_arr[i, 3:6]) for i in range(x.shape[0])]
    )
    att_angle = np.array(
        [geodesic_attitude_error_rad(x[i, 3:6], x_ref_arr[i, 3:6]) for i in range(x.shape[0])]
    )

    pos_err_norm = np.linalg.norm(e_pos, axis=1)
    rmse_pos = float(np.sqrt(np.mean(pos_err_norm**2)))
    max_pos = float(np.max(pos_err_norm))
    final_pos = float(pos_err_norm[-1])
    time_in_bounds = float(np.mean(pos_err_norm <= position_bound_m))

    # rmse_attitude_rad: RMS of geodesic angle (principal rotation)
    rmse_att = float(np.sqrt(np.mean(att_angle**2)))
    max_att = float(np.max(att_angle))
    rmse_att_vec = float(np.sqrt(np.mean(np.sum(e_att_vec**2, axis=1))))
    rmse_vel = float(np.sqrt(np.mean(np.sum(e_vel**2, axis=1))))

    # Control effort proxy: integral of ||u|| roughly via trapz on samples
    if t.size > 1:
        effort = float(np.trapezoid(np.linalg.norm(u, axis=1), t))
    else:
        effort = float(np.linalg.norm(u[0]))

    peak_thrust = float(np.max(u[:, 0]))
    peak_torque = float(np.max(np.abs(u[:, 1:4])))

    # Absolute plant envelope (not tracking error) — linearization distance proxies
    peak_roll = float(np.max(np.abs(x[:, 3])))
    peak_pitch = float(np.max(np.abs(x[:, 4])))
    peak_tilt = float(max(peak_roll, peak_pitch))
    peak_speed = float(np.max(np.linalg.norm(x[:, 6:9], axis=1)))

    # Tracking success (portfolio-honest):
    # peak |e| within 3× the study position_bound (not 5× with a 1 m floor,
    # which previously marked multi-meter AHRS paths as success=True).
    # Attitude: peak geodesic error under 45° (was 60°).
    pos_limit = 3.0 * float(position_bound_m)
    success = bool(np.isfinite(x).all() and max_pos <= pos_limit and max_att < np.deg2rad(45.0))

    return {
        "rmse_position_m": rmse_pos,
        "max_position_error_m": max_pos,
        "final_position_error_m": final_pos,
        "time_in_bounds_frac": time_in_bounds,
        "position_bound_m": position_bound_m,
        "success_pos_limit_m": pos_limit,
        "rmse_attitude_rad": rmse_att,
        "max_attitude_error_rad": max_att,
        "rmse_attitude_rotvec_rad": rmse_att_vec,
        "rmse_velocity_m_s": rmse_vel,
        "control_effort_proxy": effort,
        "peak_thrust_n": peak_thrust,
        "peak_torque_nm": peak_torque,
        "peak_tilt_rad": peak_tilt,
        "peak_roll_rad": peak_roll,
        "peak_pitch_rad": peak_pitch,
        "peak_speed_m_s": peak_speed,
        "success": success,
        "n_samples": int(t.size),
        "t_final_s": float(t[-1]) if t.size else 0.0,
        "attitude_error_model": "so3_geodesic",
        # True when RMSE used per-tick commanded x_r (required for online replan)
        "tracking_vs_commanded_reference": bool(x_ref is not None),
    }
