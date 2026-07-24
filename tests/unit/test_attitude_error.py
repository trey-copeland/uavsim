"""Phase 5c.2: SO(3) attitude error and tracking error-state."""

from __future__ import annotations

import numpy as np

from uavsim.dynamics.attitude_error import (
    geodesic_attitude_error_rad,
    rotation_error_vector_from_dcm,
    rotation_error_vector_from_euler,
    rotation_error_vector_from_quat,
    tracking_error_state,
)
from uavsim.dynamics.rotations import euler_to_quat, quat_to_euler, rotation_body_to_inertial_quat


def test_identity_error_is_zero() -> None:
    e = np.array([0.1, -0.05, 0.2])
    np.testing.assert_allclose(rotation_error_vector_from_euler(e, e), 0.0, atol=1e-14)
    assert geodesic_attitude_error_rad(e, e) < 1e-14


def test_small_angle_matches_euler_difference() -> None:
    e_ref = np.array([0.0, 0.0, 0.0])
    e = np.array([0.02, -0.01, 0.015])
    dth = rotation_error_vector_from_euler(e, e_ref)
    # SO(3) log ≈ Euler difference; O(θ²) discrepancy is expected
    np.testing.assert_allclose(dth, e - e_ref, atol=2e-4)


def test_yaw_wrap_not_2pi() -> None:
    """Naive yaw subtraction is ~2π; geodesic error is small."""
    e_ref = np.array([0.0, 0.0, np.pi - 0.05])
    e = np.array([0.0, 0.0, -np.pi + 0.05])
    naive = abs(e[2] - e_ref[2])
    assert naive > 6.0
    ang = geodesic_attitude_error_rad(e, e_ref)
    assert ang < 0.15


def test_near_180_deg_agrees_with_quat_log() -> None:
    """DCM log near π must match quat path (skew formula is 0/0 at exactly π)."""
    e_ref = np.zeros(3)
    q_id = euler_to_quat(0.0, 0.0, 0.0)
    q_flip = np.array([0.0, 1.0, 0.0, 0.0])  # 180° about body x
    d_q = rotation_error_vector_from_quat(q_flip, q_id)
    e_flip = quat_to_euler(q_flip)
    d_e = rotation_error_vector_from_euler(e_flip, e_ref)
    assert abs(float(np.linalg.norm(d_e)) - np.pi) < 1e-5
    assert abs(float(np.linalg.norm(d_q)) - np.pi) < 1e-5
    cos_align = float(np.dot(d_e, d_q) / (np.linalg.norm(d_e) * np.linalg.norm(d_q) + 1e-15))
    assert abs(abs(cos_align) - 1.0) < 1e-4
    assert abs(d_e[0]) > abs(d_e[1]) and abs(d_e[0]) > abs(d_e[2])


def test_near_180_generic_axis() -> None:
    """Off-axis 180°: DCM and quat logs agree within a tight tolerance."""
    axis = np.array([1.0, -2.0, 0.5])
    axis = axis / np.linalg.norm(axis)
    # q = [cos(π/2), sin(π/2) n] = [0, n]
    q = np.array([0.0, axis[0], axis[1], axis[2]])
    q_ref = np.array([1.0, 0.0, 0.0, 0.0])
    d_q = rotation_error_vector_from_quat(q, q_ref)
    r = rotation_body_to_inertial_quat(q)
    r_ref = rotation_body_to_inertial_quat(q_ref)
    d_r = rotation_error_vector_from_dcm(r, r_ref)
    np.testing.assert_allclose(np.linalg.norm(d_r), np.pi, atol=1e-5)
    align = abs(float(np.dot(d_r / np.linalg.norm(d_r), d_q / np.linalg.norm(d_q))))
    assert align > 0.999


def test_quat_and_euler_error_agree() -> None:
    e = np.array([0.12, -0.08, 0.4])
    er = np.array([-0.05, 0.03, -0.2])
    d_e = rotation_error_vector_from_euler(e, er)
    d_q = rotation_error_vector_from_quat(euler_to_quat(*e), euler_to_quat(*er))
    np.testing.assert_allclose(d_e, d_q, atol=1e-10)


def test_tracking_error_state_layout() -> None:
    x = np.array([1.0, 0.0, 0.0, 0.05, 0.0, 0.0, 0.1, 0.0, 0.0, 0.0, 0.0, 0.0])
    xr = np.zeros(12)
    e = tracking_error_state(x, xr)
    np.testing.assert_allclose(e[0:3], [1.0, 0.0, 0.0])
    np.testing.assert_allclose(e[3:6], rotation_error_vector_from_euler(x[3:6], xr[3:6]))
    np.testing.assert_allclose(e[6:9], [0.1, 0.0, 0.0])
