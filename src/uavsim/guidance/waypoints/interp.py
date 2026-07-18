"""MAKIMA-class smooth interpolation trajectory from waypoints."""

from __future__ import annotations

import numpy as np
from scipy.interpolate import Akima1DInterpolator

from uavsim.guidance.waypoints.mission import WaypointMission
from uavsim.guidance.waypoints.yaw import YawMode, resolve_yaw
from uavsim.reference import (
    SampledReference,
    body_rates_from_euler,
    feedforward_roll_pitch,
    pack_state_grid,
)


def generate_interp_trajectory(
    mission: WaypointMission,
    *,
    dt_s: float = 0.01,
    yaw_mode: YawMode = "constant",
    g: float = 9.81,
    backend_id: str = "waypoints.interp",
) -> SampledReference:
    """Generate C¹-ish position trajectory via SciPy Akima + numeric derivatives.

    Akima cubic Hermite avoids the zero-velocity knots of PCHIP and is the
    SciPy-available MAKIMA-class interpolant (heritage used MATLAB makima).
    """
    wpt_t = mission.time
    wpt_pos = mission.position
    t0, tf = float(wpt_t[0]), float(wpt_t[-1])
    n = max(int(np.ceil((tf - t0) / dt_s)) + 1, 2)
    t_grid = np.linspace(t0, tf, n)
    # Ensure exact endpoints
    t_grid[0] = t0
    t_grid[-1] = tf

    pos = np.zeros((n, 3), dtype=float)
    for axis in range(3):
        # method="makima" when available (SciPy ≥1.13 style); fall back to classic Akima
        try:
            interp = Akima1DInterpolator(wpt_t, wpt_pos[:, axis], method="makima")
        except TypeError:
            interp = Akima1DInterpolator(wpt_t, wpt_pos[:, axis])
        pos[:, axis] = interp(t_grid)

    vel = np.gradient(pos, t_grid, axis=0)
    acc = np.gradient(vel, t_grid, axis=0)

    yaw = resolve_yaw(
        t_grid,
        vel,
        wpt_t,
        mission.yaw,
        yaw_mode=yaw_mode,
    )
    roll, pitch = feedforward_roll_pitch(acc, g=g)
    euler = np.column_stack([roll, pitch, yaw])
    omega = body_rates_from_euler(t_grid, euler)
    x_grid = pack_state_grid(pos, vel, euler, omega)

    return SampledReference(
        t0=t0,
        tf=tf,
        backend_id=backend_id,
        metadata={
            "method": "interp",
            "interp": "makima",
            "yaw_mode": yaw_mode,
            "mission_name": mission.name,
            "n_waypoints": len(mission.waypoints),
            "dt_s": dt_s,
        },
        t_grid=t_grid,
        x_grid=x_grid,
    )
