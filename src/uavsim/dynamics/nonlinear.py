"""Nonlinear 6DOF quadrotor dynamics (heritage form)."""

from __future__ import annotations

import numpy as np

from uavsim.dynamics.rotations import euler_rate_matrix, rotation_body_to_inertial
from uavsim.vehicles.params import VehicleParams

STATE_DIM = 12
CONTROL_DIM = 4


def state_derivative(x: np.ndarray, u: np.ndarray, vehicle: VehicleParams) -> np.ndarray:
    """
    Compute ẋ for rigid-body quadrotor.

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
    f_thrust_i = r_b2i @ np.array([0.0, 0.0, -f_thrust])
    f_grav = np.array([0.0, 0.0, m * g])
    a = (f_thrust_i + f_grav) / m

    omega_dot = np.linalg.solve(inertia, tau - np.cross(omega, inertia @ omega))
    euler_dot = euler_rate_matrix(phi, theta) @ omega

    x_dot = np.zeros(STATE_DIM)
    x_dot[0:3] = v
    x_dot[3:6] = euler_dot
    x_dot[6:9] = a
    x_dot[9:12] = omega_dot
    return x_dot
