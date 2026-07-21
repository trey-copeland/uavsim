"""Attitude error for control and metrics (Phase 5c.2).

Uses the rotation-vector (axis-angle) of ``R_err = R_ref^T R`` so errors are
geodesic on SO(3), wrap-safe, and match small-angle Euler differences near hover.
Never use component-wise ``q - q_ref`` or unwrapped Euler subtraction for
tracking metrics.
"""

from __future__ import annotations

import numpy as np

from uavsim.dynamics.rotations import (
    quat_conjugate,
    quat_multiply,
    quat_normalize,
    rotation_body_to_inertial,
)

STATE_DIM = 12


def rotation_error_vector_from_dcm(r: np.ndarray, r_ref: np.ndarray) -> np.ndarray:
    """
    Body-frame rotation error vector δθ from DCMs body→inertial.

    ``R_err = R_ref^T @ R``, then δθ = vee(log(R_err)) via axis-angle.
    """
    r = np.asarray(r, dtype=float).reshape(3, 3)
    r_ref = np.asarray(r_ref, dtype=float).reshape(3, 3)
    r_err = r_ref.T @ r
    return _vee_log_so3(r_err)


def _vee_log_so3(r_err: np.ndarray) -> np.ndarray:
    """Axis-angle vector from rotation matrix (principal branch)."""
    tr = float(np.trace(r_err))
    cos_th = 0.5 * (tr - 1.0)
    cos_th = float(np.clip(cos_th, -1.0, 1.0))
    theta = float(np.arccos(cos_th))
    if theta < 1e-10:
        # First-order: vee(R - R^T)/2
        return 0.5 * np.array(
            [
                r_err[2, 1] - r_err[1, 2],
                r_err[0, 2] - r_err[2, 0],
                r_err[1, 0] - r_err[0, 1],
            ]
        )
    if theta > np.pi - 1e-6:
        # Near 180°: more careful extraction from diagonal
        # Fall back to skew-symmetric formula with sin
        pass
    w = np.array(
        [
            r_err[2, 1] - r_err[1, 2],
            r_err[0, 2] - r_err[2, 0],
            r_err[1, 0] - r_err[0, 1],
        ]
    )
    return (theta / (2.0 * np.sin(theta))) * w


def rotation_error_vector_from_euler(euler: np.ndarray, euler_ref: np.ndarray) -> np.ndarray:
    """δθ from ZYX Euler attitudes (rad)."""
    e = np.asarray(euler, dtype=float).reshape(3)
    er = np.asarray(euler_ref, dtype=float).reshape(3)
    r = rotation_body_to_inertial(float(e[0]), float(e[1]), float(e[2]))
    r_ref = rotation_body_to_inertial(float(er[0]), float(er[1]), float(er[2]))
    return rotation_error_vector_from_dcm(r, r_ref)


def rotation_error_vector_from_quat(q: np.ndarray, q_ref: np.ndarray) -> np.ndarray:
    """δθ from unit quaternions (scalar-first, body→inertial)."""
    q = quat_normalize(q)
    q_ref = quat_normalize(q_ref)
    # Shortest path: q_err = q_ref^{-1} ⊗ q
    q_err = quat_multiply(quat_conjugate(q_ref), q)
    if q_err[0] < 0.0:
        q_err = -q_err
    # For small angle: δθ ≈ 2 * q_vec; exact: 2 atan2(|v|, w) * v/|v|
    w = float(q_err[0])
    v = q_err[1:4]
    n = float(np.linalg.norm(v))
    if n < 1e-15:
        return np.zeros(3)
    angle = 2.0 * float(np.arctan2(n, w))
    return (angle / n) * v


def geodesic_attitude_error_rad(euler: np.ndarray, euler_ref: np.ndarray) -> float:
    """Principal rotation angle (rad) between two attitudes."""
    dth = rotation_error_vector_from_euler(euler, euler_ref)
    return float(np.linalg.norm(dth))


def tracking_error_state(x: np.ndarray, x_ref: np.ndarray) -> np.ndarray:
    """
    12-D tracking error for hover-style controllers (error-state form).

    ``e = [e_pos, δθ, e_vel, e_ω]`` with δθ from SO(3), not Euler subtraction.
    Expects Euler 12-state layout for both ``x`` and ``x_ref``.
    """
    x = np.asarray(x, dtype=float).reshape(STATE_DIM)
    x_ref = np.asarray(x_ref, dtype=float).reshape(STATE_DIM)
    e = np.zeros(STATE_DIM)
    e[0:3] = x[0:3] - x_ref[0:3]
    e[3:6] = rotation_error_vector_from_euler(x[3:6], x_ref[3:6])
    e[6:9] = x[6:9] - x_ref[6:9]
    e[9:12] = x[9:12] - x_ref[9:12]
    return e
