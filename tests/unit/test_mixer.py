"""Control allocation / mixer unit tests (D-8)."""

from __future__ import annotations

import numpy as np

from uavsim.dynamics.mixer import (
    N_MOTORS,
    allocation_matrix,
    hover_motor_force,
    hover_omega,
    motor_forces_to_wrench,
    omega_to_forces,
    wrench_to_motor_forces,
    wrench_to_omega_cmd,
)
from uavsim.vehicles import default_vehicle


def test_allocation_roundtrip() -> None:
    v = default_vehicle()
    b = allocation_matrix(v)
    assert b.shape == (4, N_MOTORS)
    # random feasible-ish wrench near hover
    u = v.u_hover() + np.array([0.1, 0.02, -0.015, 0.01])
    f = wrench_to_motor_forces(u, v, clip_nonnegative=False)
    u2 = motor_forces_to_wrench(f, v)
    np.testing.assert_allclose(u2, u, rtol=1e-10, atol=1e-10)


def test_hover_equal_motor_forces() -> None:
    v = default_vehicle()
    f_h = hover_motor_force(v)
    f = np.full(N_MOTORS, f_h)
    u = motor_forces_to_wrench(f, v)
    np.testing.assert_allclose(u[0], v.hover_thrust_n(), rtol=1e-10)
    np.testing.assert_allclose(u[1:], 0.0, atol=1e-10)


def test_hover_omega_and_ct() -> None:
    v = default_vehicle()
    w = hover_omega(v)
    assert 100.0 < w < 2000.0
    f = omega_to_forces(np.full(N_MOTORS, w), v.propulsion)
    np.testing.assert_allclose(f.sum(), v.hover_thrust_n(), rtol=1e-6)


def test_wrench_to_omega_cmd_positive() -> None:
    v = default_vehicle()
    w = wrench_to_omega_cmd(v.u_hover(), v)
    assert np.all(w > 0)
    np.testing.assert_allclose(w, hover_omega(v), rtol=1e-5)
