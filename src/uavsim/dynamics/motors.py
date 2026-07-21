"""First-order motor dynamics plant models (D-7) with mixer allocation (D-8).

Plant state = rigid-body state || motor speeds ω_m ∈ R⁴.
Controller still commands body wrench ``u``; the plant mixes to ω_cmd and
integrates motor lag, then applies the realized wrench to the rigid body.
"""

from __future__ import annotations

import numpy as np

from uavsim.dynamics.mixer import (
    N_MOTORS,
    hover_omega,
    motor_forces_to_wrench,
    omega_to_forces,
    wrench_to_omega_cmd,
)
from uavsim.dynamics.model import AttitudeKind, EulerRigidBodyDynamics, QuatRigidBodyDynamics
from uavsim.dynamics.nonlinear import STATE_DIM, STATE_DIM_QUAT
from uavsim.vehicles.params import VehicleParams

STATE_DIM_EULER_MOTORS = STATE_DIM + N_MOTORS  # 16
STATE_DIM_QUAT_MOTORS = STATE_DIM_QUAT + N_MOTORS  # 17


def _motor_rhs(
    omega_m: np.ndarray,
    wrench_cmd: np.ndarray,
    vehicle: VehicleParams,
) -> tuple[np.ndarray, np.ndarray]:
    """Return (ω̇_m, realized wrench from current ω_m)."""
    prop = vehicle.propulsion
    tau = max(float(prop.motor_time_const_s), 1e-6)
    omega_cmd = wrench_to_omega_cmd(wrench_cmd, vehicle)
    omega_m = np.asarray(omega_m, dtype=float).reshape(N_MOTORS)
    omega_dot = (omega_cmd - omega_m) / tau
    forces = omega_to_forces(omega_m, prop)
    u_act = motor_forces_to_wrench(forces, vehicle)
    return omega_dot, u_act


class EulerMotorDynamics:
    """12-state Euler rigid body + 4 first-order motor speeds."""

    id: str = "euler_motors"
    attitude: AttitudeKind = "euler"

    def __init__(self) -> None:
        self._rb = EulerRigidBodyDynamics()

    @property
    def state_dim(self) -> int:
        return STATE_DIM_EULER_MOTORS

    def f(self, x: np.ndarray, u: np.ndarray, vehicle: VehicleParams) -> np.ndarray:
        x = np.asarray(x, dtype=float).reshape(STATE_DIM_EULER_MOTORS)
        x_rb = x[:STATE_DIM]
        omega_m = x[STATE_DIM:]
        omega_dot, u_act = _motor_rhs(omega_m, u, vehicle)
        xdot_rb = self._rb.f(x_rb, u_act, vehicle)
        return np.concatenate([xdot_rb, omega_dot])

    def project(self, x: np.ndarray) -> np.ndarray:
        x = np.asarray(x, dtype=float).reshape(STATE_DIM_EULER_MOTORS).copy()
        x[:STATE_DIM] = self._rb.project(x[:STATE_DIM])
        prop = None  # clip motors if we had vehicle — leave unbounded in project
        _ = prop
        return x

    def to_euler_state(self, x: np.ndarray) -> np.ndarray:
        x = np.asarray(x, dtype=float).reshape(STATE_DIM_EULER_MOTORS)
        return self._rb.to_euler_state(x[:STATE_DIM])

    def from_euler_state(self, x_euler: np.ndarray) -> np.ndarray:
        """Map Euler 12-state → plant; motors at zero until reset injects hover ω."""
        x_rb = self._rb.from_euler_state(x_euler)
        return np.concatenate([x_rb, np.zeros(N_MOTORS)])

    def from_euler_state_hover_motors(
        self, x_euler: np.ndarray, vehicle: VehicleParams
    ) -> np.ndarray:
        x_rb = self._rb.from_euler_state(x_euler)
        w0 = hover_omega(vehicle)
        return np.concatenate([x_rb, np.full(N_MOTORS, w0)])


class QuatMotorDynamics:
    """13-state quaternion rigid body + 4 first-order motor speeds."""

    id: str = "quat_motors"
    attitude: AttitudeKind = "quat"

    def __init__(self) -> None:
        self._rb = QuatRigidBodyDynamics()

    @property
    def state_dim(self) -> int:
        return STATE_DIM_QUAT_MOTORS

    def f(self, x: np.ndarray, u: np.ndarray, vehicle: VehicleParams) -> np.ndarray:
        x = np.asarray(x, dtype=float).reshape(STATE_DIM_QUAT_MOTORS)
        x_rb = x[:STATE_DIM_QUAT]
        omega_m = x[STATE_DIM_QUAT:]
        omega_dot, u_act = _motor_rhs(omega_m, u, vehicle)
        xdot_rb = self._rb.f(x_rb, u_act, vehicle)
        return np.concatenate([xdot_rb, omega_dot])

    def project(self, x: np.ndarray) -> np.ndarray:
        x = np.asarray(x, dtype=float).reshape(STATE_DIM_QUAT_MOTORS).copy()
        x[:STATE_DIM_QUAT] = self._rb.project(x[:STATE_DIM_QUAT])
        return x

    def to_euler_state(self, x: np.ndarray) -> np.ndarray:
        x = np.asarray(x, dtype=float).reshape(STATE_DIM_QUAT_MOTORS)
        return self._rb.to_euler_state(x[:STATE_DIM_QUAT])

    def from_euler_state(self, x_euler: np.ndarray) -> np.ndarray:
        x_rb = self._rb.from_euler_state(x_euler)
        return np.concatenate([x_rb, np.zeros(N_MOTORS)])

    def from_euler_state_hover_motors(
        self, x_euler: np.ndarray, vehicle: VehicleParams
    ) -> np.ndarray:
        x_rb = self._rb.from_euler_state(x_euler)
        w0 = hover_omega(vehicle)
        return np.concatenate([x_rb, np.full(N_MOTORS, w0)])
