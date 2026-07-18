"""Minimum-snap trajectory generation (Mellinger-style, per-axis QP)."""

from __future__ import annotations

import math

import numpy as np

from uavsim.guidance.waypoints.mission import WaypointMission
from uavsim.guidance.waypoints.yaw import YawMode, resolve_yaw
from uavsim.reference import (
    SampledReference,
    body_rates_from_euler,
    feedforward_roll_pitch,
    pack_state_grid,
)


def _factorial(n: int) -> float:
    return float(math.factorial(n))


def poly_coeffs(t: float, derivative: int) -> np.ndarray:
    """Row vector of coefficients for d^k/dt^k of Σ c_i t^i at time t (order 7)."""
    row = np.zeros(8, dtype=float)
    for i in range(derivative, 8):
        # d^k/dt^k (t^i) = i!/(i-k)! t^(i-k)
        row[i] = _factorial(i) / _factorial(i - derivative) * (t ** (i - derivative))
    return row


def snap_hessian(duration: float) -> np.ndarray:
    """8×8 Hessian for ∫_0^T (d⁴p/dt⁴)² dt of a 7th-order polynomial."""
    h = np.zeros((8, 8), dtype=float)
    t = float(duration)
    for i in range(4, 8):
        for j in range(4, 8):
            ci = _factorial(i) / _factorial(i - 4)
            cj = _factorial(j) / _factorial(j - 4)
            power = i + j - 8
            integral = math.log(max(t, 1e-12)) if power == -1 else t ** (power + 1) / (power + 1)
            h[i, j] = ci * cj * integral
    return h


def solve_minsnap_1d(
    pos: np.ndarray,
    vel: np.ndarray,
    acc: np.ndarray,
    segment_durations: np.ndarray,
    vel_specified: np.ndarray,
    acc_specified: np.ndarray,
) -> tuple[np.ndarray, float]:
    """
    Solve min-snap for one axis.

    Returns coeffs shape (n_seg, 8) and scalar cost 0.5 c' H c.
    """
    pos = np.asarray(pos, dtype=float).reshape(-1)
    vel = np.asarray(vel, dtype=float).reshape(-1)
    acc = np.asarray(acc, dtype=float).reshape(-1)
    t_seg = np.asarray(segment_durations, dtype=float).reshape(-1)
    n = pos.size
    n_seg = n - 1
    n_coeffs = 8 * n_seg

    h = np.zeros((n_coeffs, n_coeffs), dtype=float)
    for seg in range(n_seg):
        idx = slice(seg * 8, (seg + 1) * 8)
        h[idx, idx] = snap_hessian(t_seg[seg])
    # Numerical regularization
    h = h + 1e-10 * np.eye(n_coeffs)

    a_rows: list[np.ndarray] = []
    b_vals: list[float] = []

    def add_eq(row: np.ndarray, b: float) -> None:
        a_rows.append(row)
        b_vals.append(b)

    # Start: pos, vel, acc, jerk=0
    row = np.zeros(n_coeffs)
    row[0:8] = poly_coeffs(0.0, 0)
    add_eq(row, float(pos[0]))
    row = np.zeros(n_coeffs)
    row[0:8] = poly_coeffs(0.0, 1)
    add_eq(row, float(vel[0]))
    row = np.zeros(n_coeffs)
    row[0:8] = poly_coeffs(0.0, 2)
    add_eq(row, float(acc[0]))
    row = np.zeros(n_coeffs)
    row[0:8] = poly_coeffs(0.0, 3)
    add_eq(row, 0.0)

    # Interior waypoints: pin both arriving end and departing start
    for seg in range(n_seg - 1):
        wp = seg + 1
        i_end = slice(seg * 8, (seg + 1) * 8)
        i_start = slice((seg + 1) * 8, (seg + 2) * 8)
        t_end = float(t_seg[seg])

        row = np.zeros(n_coeffs)
        row[i_end] = poly_coeffs(t_end, 0)
        add_eq(row, float(pos[wp]))
        row = np.zeros(n_coeffs)
        row[i_start] = poly_coeffs(0.0, 0)
        add_eq(row, float(pos[wp]))

        if vel_specified[wp]:
            row = np.zeros(n_coeffs)
            row[i_end] = poly_coeffs(t_end, 1)
            add_eq(row, float(vel[wp]))
            row = np.zeros(n_coeffs)
            row[i_start] = poly_coeffs(0.0, 1)
            add_eq(row, float(vel[wp]))

        if acc_specified[wp]:
            row = np.zeros(n_coeffs)
            row[i_end] = poly_coeffs(t_end, 2)
            add_eq(row, float(acc[wp]))
            row = np.zeros(n_coeffs)
            row[i_start] = poly_coeffs(0.0, 2)
            add_eq(row, float(acc[wp]))

    # End: pos, vel, acc, jerk=0
    i_last = slice((n_seg - 1) * 8, n_seg * 8)
    t_last = float(t_seg[-1])
    row = np.zeros(n_coeffs)
    row[i_last] = poly_coeffs(t_last, 0)
    add_eq(row, float(pos[-1]))
    row = np.zeros(n_coeffs)
    row[i_last] = poly_coeffs(t_last, 1)
    add_eq(row, float(vel[-1]))
    row = np.zeros(n_coeffs)
    row[i_last] = poly_coeffs(t_last, 2)
    add_eq(row, float(acc[-1]))
    row = np.zeros(n_coeffs)
    row[i_last] = poly_coeffs(t_last, 3)
    add_eq(row, 0.0)

    # Continuity of free derivatives at interiors
    for seg in range(n_seg - 1):
        wp = seg + 1
        i_cur = slice(seg * 8, (seg + 1) * 8)
        i_nxt = slice((seg + 1) * 8, (seg + 2) * 8)
        t_end = float(t_seg[seg])

        for deriv, free in (
            (1, not vel_specified[wp]),
            (2, not acc_specified[wp]),
            (3, True),  # jerk
            (4, True),  # snap
        ):
            if not free:
                continue
            row = np.zeros(n_coeffs)
            row[i_cur] = poly_coeffs(t_end, deriv)
            row[i_nxt] = -poly_coeffs(0.0, deriv)
            add_eq(row, 0.0)

    aeq = np.vstack(a_rows)
    beq = np.asarray(b_vals, dtype=float)

    # KKT system: [H  A'; A' 0] [c; λ] = [0; b]
    n_eq = aeq.shape[0]
    kkt = np.zeros((n_coeffs + n_eq, n_coeffs + n_eq), dtype=float)
    kkt[:n_coeffs, :n_coeffs] = h
    kkt[:n_coeffs, n_coeffs:] = aeq.T
    kkt[n_coeffs:, :n_coeffs] = aeq
    rhs = np.zeros(n_coeffs + n_eq, dtype=float)
    rhs[n_coeffs:] = beq

    try:
        sol = np.linalg.solve(kkt, rhs)
    except np.linalg.LinAlgError:
        sol = np.linalg.lstsq(kkt, rhs, rcond=None)[0]

    c = sol[:n_coeffs]
    cost = float(0.5 * c @ h @ c)
    coeffs = c.reshape(n_seg, 8)
    return coeffs, cost


def _eval_poly_seg(
    coeffs: np.ndarray, t_local: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Evaluate position, velocity, acceleration for one segment."""
    # p = Σ c_i t^i
    pos = np.zeros_like(t_local)
    vel = np.zeros_like(t_local)
    acc = np.zeros_like(t_local)
    for i, ci in enumerate(coeffs):
        pos += ci * t_local**i
        if i >= 1:
            vel += i * ci * t_local ** (i - 1)
        if i >= 2:
            acc += i * (i - 1) * ci * t_local ** (i - 2)
    return pos, vel, acc


def evaluate_minsnap(
    coeffs_xyz: list[np.ndarray],
    wpt_time: np.ndarray,
    segment_durations: np.ndarray,
    dt_s: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Return t, position, velocity, acceleration grids."""
    t0, tf = float(wpt_time[0]), float(wpt_time[-1])
    n = max(int(np.ceil((tf - t0) / dt_s)) + 1, 2)
    t_grid = np.linspace(t0, tf, n)
    t_grid[0] = t0
    t_grid[-1] = tf

    pos = np.zeros((n, 3))
    vel = np.zeros((n, 3))
    acc = np.zeros((n, 3))
    boundaries = np.concatenate([[wpt_time[0]], wpt_time[0] + np.cumsum(segment_durations)])

    for i, t in enumerate(t_grid):
        # Find segment
        seg = int(np.searchsorted(boundaries[1:], t, side="right"))
        seg = min(max(seg, 0), len(segment_durations) - 1)
        t_local = float(t - boundaries[seg])
        t_local = min(max(t_local, 0.0), float(segment_durations[seg]))
        for axis in range(3):
            p, v, a = _eval_poly_seg(coeffs_xyz[axis][seg], np.array([t_local]))
            pos[i, axis] = p[0]
            vel[i, axis] = v[0]
            acc[i, axis] = a[0]

    return t_grid, pos, vel, acc


def generate_minsnap_trajectory(
    mission: WaypointMission,
    *,
    dt_s: float = 0.01,
    yaw_mode: YawMode = "constant",
    g: float = 9.81,
    backend_id: str = "waypoints.minsnap",
) -> tuple[SampledReference, dict[str, float]]:
    """Generate min-snap reference; returns (reference, cost_per_axis)."""
    wpt_t = mission.time
    wpt_pos = mission.position
    vel, vel_mask = mission.velocity_specified()
    acc, acc_mask = mission.acceleration_specified()
    t_seg = np.diff(wpt_t)

    costs: dict[str, float] = {}
    coeffs_xyz: list[np.ndarray] = []
    for axis, name in enumerate("xyz"):
        c, cost = solve_minsnap_1d(
            wpt_pos[:, axis],
            vel[:, axis],
            acc[:, axis],
            t_seg,
            vel_mask,
            acc_mask,
        )
        coeffs_xyz.append(c)
        costs[name] = cost

    t_grid, pos, vel_g, acc_g = evaluate_minsnap(coeffs_xyz, wpt_t, t_seg, dt_s)
    yaw = resolve_yaw(t_grid, vel_g, wpt_t, mission.yaw, yaw_mode=yaw_mode)
    roll, pitch = feedforward_roll_pitch(acc_g, g=g)
    euler = np.column_stack([roll, pitch, yaw])
    omega = body_rates_from_euler(t_grid, euler)
    x_grid = pack_state_grid(pos, vel_g, euler, omega)

    ref = SampledReference(
        t0=float(t_grid[0]),
        tf=float(t_grid[-1]),
        backend_id=backend_id,
        metadata={
            "method": "minsnap",
            "yaw_mode": yaw_mode,
            "mission_name": mission.name,
            "n_waypoints": len(mission.waypoints),
            "dt_s": dt_s,
            "snap_cost": costs,
        },
        t_grid=t_grid,
        x_grid=x_grid,
    )
    return ref, costs
