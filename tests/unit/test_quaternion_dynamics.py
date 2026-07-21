"""Phase 5c.1: quaternion plant kinematics and Euler parity."""

from __future__ import annotations

import numpy as np

from uavsim.dynamics import (
    euler_state_to_quat_state,
    euler_to_quat,
    integrate_fixed_step,
    quat_state_to_euler_state,
    quat_to_euler,
    renormalize_quat_state,
    rotation_body_to_inertial,
    rotation_body_to_inertial_quat,
    state_derivative,
    state_derivative_quat,
)
from uavsim.vehicles import default_vehicle


def test_euler_quat_roundtrip_small_attitudes() -> None:
    for angles in (
        (0.0, 0.0, 0.0),
        (0.1, -0.05, 0.2),
        (-0.3, 0.15, -0.4),
        (0.5, -0.4, 1.0),
    ):
        q = euler_to_quat(*angles)
        assert abs(np.linalg.norm(q) - 1.0) < 1e-12
        back = quat_to_euler(q)
        np.testing.assert_allclose(back, angles, atol=1e-9)


def test_rotation_matrix_matches_euler_path() -> None:
    phi, theta, psi = 0.12, -0.08, 0.35
    r_e = rotation_body_to_inertial(phi, theta, psi)
    r_q = rotation_body_to_inertial_quat(euler_to_quat(phi, theta, psi))
    np.testing.assert_allclose(r_q, r_e, atol=1e-12)


def test_quat_hover_trim_derivative_near_zero() -> None:
    vehicle = default_vehicle()
    x = np.zeros(13)
    x[3] = 1.0  # identity quat
    u = vehicle.u_hover()
    x_dot = state_derivative_quat(x, u, vehicle)
    assert np.linalg.norm(x_dot) < 1e-10


def test_state_layout_conversions() -> None:
    x_e = np.array([1.0, 2.0, 3.0, 0.05, -0.02, 0.1, 0.1, 0.0, -0.2, 0.01, -0.02, 0.03])
    x_q = euler_state_to_quat_state(x_e)
    assert x_q.shape == (13,)
    back = quat_state_to_euler_state(x_q)
    np.testing.assert_allclose(back[0:3], x_e[0:3])
    np.testing.assert_allclose(back[3:6], x_e[3:6], atol=1e-12)
    np.testing.assert_allclose(back[6:12], x_e[6:12])


def test_renormalize_restores_unit_and_positive_scalar() -> None:
    x = np.zeros(13)
    x[3:7] = np.array([-2.0, 0.0, 0.0, 0.0])  # non-unit, negative scalar
    y = renormalize_quat_state(x)
    np.testing.assert_allclose(np.linalg.norm(y[3:7]), 1.0, atol=1e-15)
    assert y[3] > 0.0


def test_open_loop_parity_euler_vs_quat_gentle() -> None:
    """
    Same body wrench history: position and attitude (via Euler extract) match
    within integration tolerance on a gentle maneuver (no pitch singularity).
    """
    vehicle = default_vehicle()
    # Mild rates + slight tilt so both kinematics are well-conditioned
    x0_e = np.zeros(12)
    x0_e[3:6] = [0.05, -0.03, 0.1]
    x0_e[9:12] = [0.2, -0.15, 0.1]
    x0_q = euler_state_to_quat_state(x0_e)

    def u_fn(_t: float, _x: np.ndarray) -> np.ndarray:
        u = vehicle.u_hover().copy()
        u[1:4] = [0.002, -0.0015, 0.0005]  # small torques
        return u

    t_e, xs_e = integrate_fixed_step(
        x0_e, u_fn, vehicle, t0=0.0, tf=2.0, dt=0.005, attitude="euler"
    )
    t_q, xs_q = integrate_fixed_step(
        x0_q, u_fn, vehicle, t0=0.0, tf=2.0, dt=0.005, attitude="quat"
    )
    np.testing.assert_allclose(t_e, t_q)

    # Convert quat trajectory to Euler for comparison
    xs_q_as_e = np.vstack([quat_state_to_euler_state(xi) for xi in xs_q])

    # Position / velocity / rates should track closely
    np.testing.assert_allclose(xs_q_as_e[:, 0:3], xs_e[:, 0:3], atol=2e-4, rtol=0)
    np.testing.assert_allclose(xs_q_as_e[:, 6:12], xs_e[:, 6:12], atol=5e-4, rtol=0)
    # Attitude: wrap-safe component errors
    d_att = xs_q_as_e[:, 3:6] - xs_e[:, 3:6]
    d_att = (d_att + np.pi) % (2 * np.pi) - np.pi
    assert np.max(np.abs(d_att)) < 2e-3

    # Quaternion stays unit throughout
    norms = np.linalg.norm(xs_q[:, 3:7], axis=1)
    np.testing.assert_allclose(norms, 1.0, atol=1e-12)


def test_quat_and_euler_rhs_match_at_aligned_state() -> None:
    """Instantaneous ẋ for pos/vel/omega agree when attitude is identical."""
    vehicle = default_vehicle()
    x_e = np.array([0.0, 0.0, 1.0, 0.08, -0.05, 0.2, 0.1, -0.05, 0.0, 0.05, -0.02, 0.01])
    x_q = euler_state_to_quat_state(x_e)
    u = vehicle.u_hover().copy()
    u[0] *= 1.05
    u[1:4] = [0.01, -0.008, 0.002]

    de = state_derivative(x_e, u, vehicle)
    dq = state_derivative_quat(x_q, u, vehicle)

    np.testing.assert_allclose(dq[0:3], de[0:3], atol=1e-14)
    np.testing.assert_allclose(dq[7:10], de[6:9], atol=1e-14)
    np.testing.assert_allclose(dq[10:13], de[9:12], atol=1e-14)

    # Quaternion rate should be consistent with Euler rate via chain rule check:
    # finite-diff euler_to_quat along euler_dot ≈ q_dot
    eps = 1e-7
    e0 = x_e[3:6]
    e1 = e0 + eps * de[3:6]
    q0 = euler_to_quat(float(e0[0]), float(e0[1]), float(e0[2]))
    q1 = euler_to_quat(float(e1[0]), float(e1[1]), float(e1[2]))
    # Align hemisphere
    if np.dot(q0, q1) < 0:
        q1 = -q1
    q_dot_fd = (q1 - q0) / eps
    q_dot = dq[3:7]
    # Align fd to continuous q_dot direction
    if np.dot(q_dot_fd, q_dot) < 0:
        q_dot_fd = -q_dot_fd
    np.testing.assert_allclose(q_dot, q_dot_fd, atol=5e-5, rtol=0)


def test_quat_stays_unit_under_spin() -> None:
    vehicle = default_vehicle()
    x0 = np.zeros(13)
    x0[3] = 1.0
    x0[10:13] = [1.0, 0.5, -0.25]  # sustained spin

    def u_fn(_t: float, _x: np.ndarray) -> np.ndarray:
        return vehicle.u_hover()

    _t, xs = integrate_fixed_step(
        x0, u_fn, vehicle, t0=0.0, tf=5.0, dt=0.01, attitude="quat"
    )
    norms = np.linalg.norm(xs[:, 3:7], axis=1)
    np.testing.assert_allclose(norms, 1.0, atol=1e-11)
    # Should not collapse to NaN
    assert np.isfinite(xs).all()
