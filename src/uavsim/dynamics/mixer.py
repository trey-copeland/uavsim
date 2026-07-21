"""Control allocation / multirotor mixer (D-8).

Maps body wrench ``u = [F, τφ, τθ, τψ]`` ↔ per-motor forces (and ω² via CT).
Layout: **X-configuration** quadrotor in FRD body frame.

Motor index (top view, +x forward, +y right)::

      front
   4       1
     \\   /
      \\ /
      / \\
     /   \\
   3       2
      rear

Spin: 1 & 3 one way, 2 & 4 opposite (yaw from reaction torque).
"""

from __future__ import annotations

import numpy as np

from uavsim.dynamics.nonlinear import CONTROL_DIM
from uavsim.vehicles.params import PropulsionParams, VehicleParams

N_MOTORS = 4


def lever_arm_m(vehicle: VehicleParams) -> float:
    """Moment arm for X layout: arm_length / √2 (center to motor axis projection)."""
    return float(vehicle.arm_length_m) / np.sqrt(2.0)


def yaw_force_coeff(prop: PropulsionParams) -> float:
    """Map motor force → signed yaw torque magnitude: |τ_i| = (cq/ct) f_i."""
    return float(prop.cq_nm_s2) / max(float(prop.ct_n_s2), 1e-18)


def allocation_matrix(vehicle: VehicleParams) -> np.ndarray:
    """
    B (4×4) such that ``u = B @ f`` with motor forces ``f ≥ 0``.

    Rows: total thrust, roll torque, pitch torque, yaw torque.
    """
    prop = vehicle.propulsion
    ell = lever_arm_m(vehicle)
    k = yaw_force_coeff(prop)
    # Columns = motors 1..4
    return np.array(
        [
            [1.0, 1.0, 1.0, 1.0],
            [ell, -ell, -ell, ell],
            [ell, ell, -ell, -ell],
            [k, -k, k, -k],
        ],
        dtype=float,
    )


def motor_forces_to_wrench(forces: np.ndarray, vehicle: VehicleParams) -> np.ndarray:
    """Forward allocation: motor forces → body wrench."""
    f = np.asarray(forces, dtype=float).reshape(N_MOTORS)
    return allocation_matrix(vehicle) @ f


def wrench_to_motor_forces(
    wrench: np.ndarray,
    vehicle: VehicleParams,
    *,
    clip_nonnegative: bool = True,
) -> np.ndarray:
    """
    Inverse allocation: body wrench → motor forces.

    Uses ``B^{-1}`` (square X-quad). Negative forces are clipped to 0 when
    ``clip_nonnegative`` (infeasible wrench / saturation).
    """
    u = np.asarray(wrench, dtype=float).reshape(CONTROL_DIM)
    b = allocation_matrix(vehicle)
    f = np.linalg.solve(b, u)
    if clip_nonnegative:
        f = np.maximum(f, 0.0)
    return f


def forces_to_omega(forces: np.ndarray, prop: PropulsionParams) -> np.ndarray:
    """Thrust model ``f = ct ω²`` → ``ω = sqrt(f/ct)`` (nonnegative)."""
    f = np.asarray(forces, dtype=float).reshape(N_MOTORS)
    ct = max(float(prop.ct_n_s2), 1e-18)
    return np.sqrt(np.maximum(f, 0.0) / ct)


def omega_to_forces(omega: np.ndarray, prop: PropulsionParams) -> np.ndarray:
    """``f = ct ω²``."""
    w = np.asarray(omega, dtype=float).reshape(N_MOTORS)
    return float(prop.ct_n_s2) * np.maximum(w, 0.0) ** 2


def hover_motor_force(vehicle: VehicleParams) -> float:
    return float(vehicle.hover_thrust_n()) / N_MOTORS


def hover_omega(vehicle: VehicleParams) -> float:
    f_h = hover_motor_force(vehicle)
    return float(forces_to_omega(np.full(N_MOTORS, f_h), vehicle.propulsion)[0])


def clip_omega(omega: np.ndarray, prop: PropulsionParams) -> np.ndarray:
    w = np.asarray(omega, dtype=float).reshape(N_MOTORS)
    return np.clip(w, prop.omega_min_rad_s, prop.omega_max_rad_s)


def wrench_to_omega_cmd(wrench: np.ndarray, vehicle: VehicleParams) -> np.ndarray:
    """Desired motor speeds from a commanded body wrench (via force mix + CT)."""
    f = wrench_to_motor_forces(wrench, vehicle, clip_nonnegative=True)
    # Cap force by max thrust capability of one motor
    f_max = float(vehicle.propulsion.ct_n_s2) * float(vehicle.propulsion.omega_max_rad_s) ** 2
    f = np.minimum(f, f_max)
    return clip_omega(forces_to_omega(f, vehicle.propulsion), vehicle.propulsion)
