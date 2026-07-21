"""Plant dynamics: f(x, u, p), linearization, trim helpers."""

from uavsim.dynamics.attitude_error import (
    geodesic_attitude_error_rad,
    rotation_error_vector_from_euler,
    tracking_error_state,
)
from uavsim.dynamics.linearize import hover_linearization
from uavsim.dynamics.mixer import (
    N_MOTORS,
    allocation_matrix,
    hover_omega,
    motor_forces_to_wrench,
    wrench_to_motor_forces,
    wrench_to_omega_cmd,
)
from uavsim.dynamics.model import (
    DynamicsModel,
    EulerRigidBodyDynamics,
    PlantKind,
    QuatRigidBodyDynamics,
    get_dynamics_model,
)
from uavsim.dynamics.motors import (
    STATE_DIM_EULER_MOTORS,
    STATE_DIM_QUAT_MOTORS,
    EulerMotorDynamics,
    QuatMotorDynamics,
)
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
    "DynamicsModel",
    "EulerMotorDynamics",
    "EulerRigidBodyDynamics",
    "N_MOTORS",
    "PlantKind",
    "QuatMotorDynamics",
    "QuatRigidBodyDynamics",
    "STATE_DIM",
    "STATE_DIM_EULER_MOTORS",
    "STATE_DIM_QUAT",
    "STATE_DIM_QUAT_MOTORS",
    "allocation_matrix",
    "euler_state_to_quat_state",
    "euler_to_quat",
    "geodesic_attitude_error_rad",
    "get_dynamics_model",
    "hover_linearization",
    "hover_omega",
    "integrate_fixed_step",
    "motor_forces_to_wrench",
    "quat_normalize",
    "quat_state_to_euler_state",
    "quat_to_euler",
    "renormalize_quat_state",
    "rotation_body_to_inertial",
    "rotation_body_to_inertial_quat",
    "rotation_error_vector_from_euler",
    "state_derivative",
    "state_derivative_quat",
    "tracking_error_state",
    "wrench_to_motor_forces",
    "wrench_to_omega_cmd",
]
