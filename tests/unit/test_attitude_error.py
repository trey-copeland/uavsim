"""Phase 5c.2: SO(3) attitude error and tracking error-state."""

from __future__ import annotations

import numpy as np

from uavsim.dynamics.attitude_error import (
    geodesic_attitude_error_rad,
    rotation_error_vector_from_euler,
    rotation_error_vector_from_quat,
    tracking_error_state,
)
from uavsim.dynamics.rotations import euler_to_quat


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
