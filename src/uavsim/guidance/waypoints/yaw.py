"""Yaw trajectory policies for waypoint guidance."""

from __future__ import annotations

from typing import Literal

import numpy as np
from scipy.interpolate import interp1d

YawMode = Literal["constant", "path_tangent", "from_waypoints"]


def resolve_yaw(
    t_grid: np.ndarray,
    velocity_ned: np.ndarray,
    wpt_time: np.ndarray,
    wpt_yaw: np.ndarray,
    *,
    yaw_mode: YawMode = "constant",
    constant_yaw_rad: float = 0.0,
    path_tangent_speed_eps: float = 0.05,
) -> np.ndarray:
    """
    Build yaw(t) on ``t_grid``.

    - ``constant``: fixed heading (default 0, or first finite waypoint yaw).
    - ``path_tangent``: atan2(v_e, v_n) with hold-last when slow.
    - ``from_waypoints``: interpolate explicit waypoint yaws; NaN → path tangent fill.
    """
    t_grid = np.asarray(t_grid, dtype=float)
    n = t_grid.size
    yaw = np.zeros(n, dtype=float)

    if yaw_mode == "constant":
        y0 = constant_yaw_rad
        finite = wpt_yaw[np.isfinite(wpt_yaw)]
        if finite.size:
            y0 = float(finite[0])
        yaw[:] = y0
        return yaw

    if yaw_mode == "path_tangent":
        return _path_tangent_yaw(velocity_ned, path_tangent_speed_eps)

    if yaw_mode == "from_waypoints":
        # Interpolate finite waypoints; fill NaN segments with path tangent
        finite_mask = np.isfinite(wpt_yaw)
        if not np.any(finite_mask):
            return _path_tangent_yaw(velocity_ned, path_tangent_speed_eps)
        if np.all(finite_mask):
            f = interp1d(
                wpt_time,
                _unwrap_series(wpt_yaw),
                kind="linear",
                bounds_error=False,
                fill_value=(float(wpt_yaw[0]), float(wpt_yaw[-1])),
            )
            return np.asarray(f(t_grid), dtype=float)

        # Mixed: start from path tangent then override with interpolated finite yaws
        yaw = _path_tangent_yaw(velocity_ned, path_tangent_speed_eps)
        f = interp1d(
            wpt_time[finite_mask],
            _unwrap_series(wpt_yaw[finite_mask]),
            kind="linear",
            bounds_error=False,
            fill_value="extrapolate",
        )
        # Only trust interp between first and last finite times
        t_lo, t_hi = wpt_time[finite_mask][0], wpt_time[finite_mask][-1]
        mid = (t_grid >= t_lo) & (t_grid <= t_hi)
        yaw[mid] = f(t_grid[mid])
        return yaw

    msg = f"Unknown yaw_mode: {yaw_mode!r}"
    raise ValueError(msg)


def _path_tangent_yaw(velocity_ned: np.ndarray, speed_eps: float) -> np.ndarray:
    vn = velocity_ned[:, 0]
    ve = velocity_ned[:, 1]
    speed_h = np.hypot(vn, ve)
    raw = np.arctan2(ve, vn)
    yaw = np.zeros(len(raw), dtype=float)
    last = 0.0
    for i in range(len(raw)):
        if speed_h[i] >= speed_eps:
            last = float(raw[i])
        yaw[i] = last
    # Unwrap for smoothness
    return np.unwrap(yaw)


def _unwrap_series(yaw: np.ndarray) -> np.ndarray:
    return np.unwrap(np.asarray(yaw, dtype=float))
