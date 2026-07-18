"""Tracking and control metrics."""

from __future__ import annotations

from typing import Any

import numpy as np

from uavsim.reference import ReferenceTrajectory


def compute_metrics(
    t: np.ndarray,
    x: np.ndarray,
    u: np.ndarray,
    reference: ReferenceTrajectory,
    *,
    position_bound_m: float = 0.1,
) -> dict[str, Any]:
    x_ref = np.vstack([reference.evaluate(float(ti)).x_ref for ti in t])
    e_pos = x[:, 0:3] - x_ref[:, 0:3]
    e_att = x[:, 3:6] - x_ref[:, 3:6]
    e_vel = x[:, 6:9] - x_ref[:, 6:9]

    pos_err_norm = np.linalg.norm(e_pos, axis=1)
    rmse_pos = float(np.sqrt(np.mean(pos_err_norm**2)))
    max_pos = float(np.max(pos_err_norm))
    final_pos = float(pos_err_norm[-1])
    time_in_bounds = float(np.mean(pos_err_norm <= position_bound_m))

    rmse_att = float(np.sqrt(np.mean(np.sum(e_att**2, axis=1))))
    max_att = float(np.max(np.abs(e_att)))
    rmse_vel = float(np.sqrt(np.mean(np.sum(e_vel**2, axis=1))))

    # Control effort proxy: integral of ||u|| roughly via trapz on samples
    if t.size > 1:
        effort = float(np.trapezoid(np.linalg.norm(u, axis=1), t))
    else:
        effort = float(np.linalg.norm(u[0]))

    peak_thrust = float(np.max(u[:, 0]))
    peak_torque = float(np.max(np.abs(u[:, 1:4])))

    success = bool(
        np.isfinite(x).all()
        and max_pos < max(5.0 * position_bound_m, 1.0)
        and max_att < np.deg2rad(60.0)
    )

    return {
        "rmse_position_m": rmse_pos,
        "max_position_error_m": max_pos,
        "final_position_error_m": final_pos,
        "time_in_bounds_frac": time_in_bounds,
        "position_bound_m": position_bound_m,
        "rmse_attitude_rad": rmse_att,
        "max_attitude_error_rad": max_att,
        "rmse_velocity_m_s": rmse_vel,
        "control_effort_proxy": effort,
        "peak_thrust_n": peak_thrust,
        "peak_torque_nm": peak_torque,
        "success": success,
        "n_samples": int(t.size),
        "t_final_s": float(t[-1]) if t.size else 0.0,
    }
