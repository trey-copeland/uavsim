"""Plant dynamics: f(x, u, p), linearization, trim helpers."""

from uavsim.dynamics.linearize import hover_linearization
from uavsim.dynamics.nonlinear import (
    CONTROL_DIM,
    STATE_DIM,
    STATE_DIM_QUAT,
    euler_state_to_quat_state,
    integrate_fixed_step,
    quat_state_to_euler_state,
    renormalize_quat_state,
    state_derivative,
    state_derivative_quat,
)
from uavsim.dynamics.rotations import (
    euler_to_quat,
    quat_normalize,
    quat_to_euler,
    rotation_body_to_inertial,
    rotation_body_to_inertial_quat,
)

__all__ = [
    "CONTROL_DIM",
    "STATE_DIM",
    "STATE_DIM_QUAT",
    "euler_state_to_quat_state",
    "euler_to_quat",
    "hover_linearization",
    "integrate_fixed_step",
    "quat_normalize",
    "quat_state_to_euler_state",
    "quat_to_euler",
    "renormalize_quat_state",
    "rotation_body_to_inertial",
    "rotation_body_to_inertial_quat",
    "state_derivative",
    "state_derivative_quat",
]
