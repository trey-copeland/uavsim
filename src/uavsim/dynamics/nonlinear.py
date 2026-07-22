"""Nonlinear 6DOF quadrotor dynamics (heritage Euler + Phase 5c quaternion)."""

from __future__ import annotations

import numpy as np

from uavsim.dynamics.aero import apply_aero
from uavsim.dynamics.rotations import (
    euler_rate_matrix,
    euler_to_quat,
    quat_derivative_body_rates,
    quat_normalize,
    quat_to_euler,
    rotation_body_to_inertial,
    rotation_body_to_inertial_quat,
)
from uavsim.vehicles.params import VehicleParams

# Euler state (shipped core / control path today)
STATE_DIM = 12
# Quaternion plant state (Phase 5c.1): pos(3) + quat(4) + vel(3) + omega(3)
STATE_DIM_QUAT = 13
CONTROL_DIM = 4


def state_derivative(x: np.ndarray, u: np.ndarray, vehicle: VehicleParams) -> np.ndarray:
    """
    Compute ẋ for rigid-body quadrotor (Euler attitude).

    State (NED): [x,y,z, φ,θ,ψ, ẋ,ẏ,ż, p,q,r]
    Control: [F, τφ, τθ, τψ] — thrust along −body-z; torques in body frame.
    """
    x = np.asarray(x, dtype=float).reshape(STATE_DIM)
    u = np.asarray(u, dtype=float).reshape(CONTROL_DIM)

    phi, theta, psi = x[3], x[4], x[5]
    v = x[6:9]
    omega = x[9:12]
    f_thrust = float(u[0])
    tau = u[1:4]

    m = vehicle.mass_kg
    g = vehicle.gravity_m_s2
    inertia = vehicle.inertia.as_diag()

    r_b2i = rotation_body_to_inertial(phi, theta, psi)
    f_thrust_eff, f_aero_i, tau_eff, _kappa = apply_aero(
        z_ned_m=float(x[2]),
        v_ned=v,
        omega_body=omega,
        r_b2i=r_b2i,
        thrust_n=f_thrust,
        tau_body=tau,
        vehicle=vehicle,
    )
    f_thrust_i = r_b2i @ np.array([0.0, 0.0, -f_thrust_eff])
    f_grav = np.array([0.0, 0.0, m * g])
    a = (f_thrust_i + f_grav + f_aero_i) / m

    omega_dot = np.linalg.solve(inertia, tau_eff - np.cross(omega, inertia @ omega))
    euler_dot = euler_rate_matrix(phi, theta) @ omega

    x_dot = np.zeros(STATE_DIM)
    x_dot[0:3] = v
    x_dot[3:6] = euler_dot
    x_dot[6:9] = a
    x_dot[9:12] = omega_dot
    return x_dot


def state_derivative_quat(x: np.ndarray, u: np.ndarray, vehicle: VehicleParams) -> np.ndarray:
    """
    Compute ẋ for rigid-body quadrotor with unit-quaternion attitude.

    State (NED): [x,y,z, qw,qx,qy,qz, ẋ,ẏ,ż, p,q,r]  (length 13)
    Control: same body wrench as :func:`state_derivative`.

    Callers that integrate must **renormalize** the quaternion after each step
    (see :func:`renormalize_quat_state`).
    """
    x = np.asarray(x, dtype=float).reshape(STATE_DIM_QUAT)
    u = np.asarray(u, dtype=float).reshape(CONTROL_DIM)

    q = quat_normalize(x[3:7])
    v = x[7:10]
    omega = x[10:13]
    f_thrust = float(u[0])
    tau = u[1:4]

    m = vehicle.mass_kg
    g = vehicle.gravity_m_s2
    inertia = vehicle.inertia.as_diag()

    r_b2i = rotation_body_to_inertial_quat(q)
    f_thrust_eff, f_aero_i, tau_eff, _kappa = apply_aero(
        z_ned_m=float(x[2]),
        v_ned=v,
        omega_body=omega,
        r_b2i=r_b2i,
        thrust_n=f_thrust,
        tau_body=tau,
        vehicle=vehicle,
    )
    f_thrust_i = r_b2i @ np.array([0.0, 0.0, -f_thrust_eff])
    f_grav = np.array([0.0, 0.0, m * g])
    a = (f_thrust_i + f_grav + f_aero_i) / m

    omega_dot = np.linalg.solve(inertia, tau_eff - np.cross(omega, inertia @ omega))
    q_dot = quat_derivative_body_rates(q, omega)

    x_dot = np.zeros(STATE_DIM_QUAT)
    x_dot[0:3] = v
    x_dot[3:7] = q_dot
    x_dot[7:10] = a
    x_dot[10:13] = omega_dot
    return x_dot


def renormalize_quat_state(x: np.ndarray) -> np.ndarray:
    """Copy of 13-state vector with unit quaternion block."""
    x = np.asarray(x, dtype=float).reshape(STATE_DIM_QUAT).copy()
    x[3:7] = quat_normalize(x[3:7])
    # Prefer positive scalar hemisphere for continuity in comparisons
    if x[3] < 0.0:
        x[3:7] *= -1.0
    return x


def euler_state_to_quat_state(x: np.ndarray) -> np.ndarray:
    """Map 12-state Euler vector → 13-state quaternion vector."""
    x = np.asarray(x, dtype=float).reshape(STATE_DIM)
    q = euler_to_quat(float(x[3]), float(x[4]), float(x[5]))
    out = np.zeros(STATE_DIM_QUAT)
    out[0:3] = x[0:3]
    out[3:7] = q
    out[7:10] = x[6:9]
    out[10:13] = x[9:12]
    return out


def quat_state_to_euler_state(x: np.ndarray) -> np.ndarray:
    """Map 13-state quaternion vector → 12-state Euler vector."""
    x = renormalize_quat_state(x)
    eul = quat_to_euler(x[3:7])
    out = np.zeros(STATE_DIM)
    out[0:3] = x[0:3]
    out[3:6] = eul
    out[6:9] = x[7:10]
    out[9:12] = x[10:13]
    return out


def integrate_fixed_step(
    x0: np.ndarray,
    u_fn,
    vehicle: VehicleParams,
    *,
    t0: float,
    tf: float,
    dt: float,
    attitude: str = "euler",
) -> tuple[np.ndarray, np.ndarray]:
    """
    RK4 fixed-step open integration for plant comparison tests.

    ``u_fn(t, x) -> u``; ``attitude`` is ``\"euler\"`` or ``\"quat\"``.
    Quaternion path renormalizes after every step.
    """
    if attitude not in ("euler", "quat"):
        msg = f"attitude must be 'euler' or 'quat', got {attitude!r}"
        raise ValueError(msg)
    if dt <= 0 or tf < t0:
        msg = "require dt > 0 and tf >= t0"
        raise ValueError(msg)

    n_steps = int(np.ceil((tf - t0) / dt))
    t_grid = t0 + dt * np.arange(n_steps + 1)
    if t_grid[-1] > tf:
        t_grid[-1] = tf

    if attitude == "euler":
        dim = STATE_DIM
        f = state_derivative
        x = np.asarray(x0, dtype=float).reshape(dim).copy()
    else:
        dim = STATE_DIM_QUAT
        f = state_derivative_quat
        x = renormalize_quat_state(x0)

    xs = np.zeros((t_grid.size, dim))
    xs[0] = x
    for i in range(n_steps):
        ti = float(t_grid[i])
        dti = float(t_grid[i + 1] - t_grid[i])
        ui = np.asarray(u_fn(ti, x), dtype=float).reshape(CONTROL_DIM)

        def f_at(tt: float, xx: np.ndarray, uu: np.ndarray = ui) -> np.ndarray:
            return f(xx, uu, vehicle)

        k1 = f_at(ti, x)
        k2 = f_at(ti + 0.5 * dti, x + 0.5 * dti * k1)
        k3 = f_at(ti + 0.5 * dti, x + 0.5 * dti * k2)
        k4 = f_at(ti + dti, x + dti * k3)
        x = x + (dti / 6.0) * (k1 + 2 * k2 + 2 * k3 + k4)
        if attitude == "quat":
            x = renormalize_quat_state(x)
        xs[i + 1] = x
    return t_grid, xs
