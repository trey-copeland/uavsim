"""Pluggable plant dynamics (Phase 5c.4 / D-3).

Default implementations wrap the rigid-body Euler and quaternion plants.
Future motors, drag, and flexible modes implement :class:`DynamicsModel`
without rewriting ``SimPlant`` / closed-loop.
"""

from __future__ import annotations

from typing import Literal, Protocol, runtime_checkable

import numpy as np

from uavsim.dynamics.nonlinear import (
    STATE_DIM,
    STATE_DIM_QUAT,
    euler_state_to_quat_state,
    quat_state_to_euler_state,
    renormalize_quat_state,
    state_derivative,
    state_derivative_quat,
)
from uavsim.vehicles.params import VehicleParams

AttitudeKind = Literal["euler", "quat"]


@runtime_checkable
class DynamicsModel(Protocol):
    """Plant model: state derivative + layout bridges for control/metrics."""

    id: str
    attitude: AttitudeKind

    @property
    def state_dim(self) -> int: ...

    def f(self, x: np.ndarray, u: np.ndarray, vehicle: VehicleParams) -> np.ndarray:
        """Continuous-time ẋ = f(x, u; vehicle)."""
        ...

    def project(self, x: np.ndarray) -> np.ndarray:
        """Optional manifold projection (e.g. unit quaternion)."""
        ...

    def to_euler_state(self, x: np.ndarray) -> np.ndarray:
        """Map plant state → Euler 12-state for controllers / metrics."""
        ...

    def from_euler_state(self, x_euler: np.ndarray) -> np.ndarray:
        """Map Euler 12-state → plant state (e.g. at reset)."""
        ...


class EulerRigidBodyDynamics:
    """Shipped 12-state ZYX Euler rigid-body quadrotor."""

    id: str = "euler_rigid_body"
    attitude: AttitudeKind = "euler"

    @property
    def state_dim(self) -> int:
        return STATE_DIM

    def f(self, x: np.ndarray, u: np.ndarray, vehicle: VehicleParams) -> np.ndarray:
        return state_derivative(x, u, vehicle)

    def project(self, x: np.ndarray) -> np.ndarray:
        return np.asarray(x, dtype=float).reshape(STATE_DIM).copy()

    def to_euler_state(self, x: np.ndarray) -> np.ndarray:
        return np.asarray(x, dtype=float).reshape(STATE_DIM).copy()

    def from_euler_state(self, x_euler: np.ndarray) -> np.ndarray:
        return np.asarray(x_euler, dtype=float).reshape(STATE_DIM).copy()


class QuatRigidBodyDynamics:
    """13-state unit-quaternion rigid-body quadrotor (Phase 5c)."""

    id: str = "quat_rigid_body"
    attitude: AttitudeKind = "quat"

    @property
    def state_dim(self) -> int:
        return STATE_DIM_QUAT

    def f(self, x: np.ndarray, u: np.ndarray, vehicle: VehicleParams) -> np.ndarray:
        return state_derivative_quat(x, u, vehicle)

    def project(self, x: np.ndarray) -> np.ndarray:
        return renormalize_quat_state(x)

    def to_euler_state(self, x: np.ndarray) -> np.ndarray:
        return quat_state_to_euler_state(x)

    def from_euler_state(self, x_euler: np.ndarray) -> np.ndarray:
        return euler_state_to_quat_state(x_euler)


def get_dynamics_model(attitude: AttitudeKind = "euler") -> DynamicsModel:
    """Factory for built-in rigid-body models."""
    if attitude == "euler":
        return EulerRigidBodyDynamics()
    if attitude == "quat":
        return QuatRigidBodyDynamics()
    msg = f"Unknown attitude model {attitude!r}"
    raise ValueError(msg)
