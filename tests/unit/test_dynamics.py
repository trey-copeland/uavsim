"""Unit tests for nonlinear dynamics and hover linearization."""

from __future__ import annotations

import numpy as np

from uavsim.dynamics import hover_linearization, state_derivative
from uavsim.vehicles import default_vehicle


def test_hover_trim_derivative_near_zero() -> None:
    vehicle = default_vehicle()
    x = np.zeros(12)
    u = vehicle.u_hover()
    x_dot = state_derivative(x, u, vehicle)
    assert np.linalg.norm(x_dot) < 1e-10


def test_hover_thrust_force_balance() -> None:
    vehicle = default_vehicle()
    assert abs(vehicle.hover_thrust_n() - vehicle.mass_kg * vehicle.gravity_m_s2) < 1e-12


def test_positive_thrust_produces_negative_z_accel_in_ned() -> None:
    """Extra thrust (beyond hover) accelerates upward = −z in NED."""
    vehicle = default_vehicle()
    x = np.zeros(12)
    u = vehicle.u_hover().copy()
    u[0] *= 1.5
    x_dot = state_derivative(x, u, vehicle)
    assert x_dot[8] < 0.0  # ż


def test_tilt_to_accel_signs_match_linearization() -> None:
    """+θ → a_north < 0; +φ → a_east > 0 (NED, thrust −body-z)."""
    vehicle = default_vehicle()
    u = vehicle.u_hover()
    x_p = np.zeros(12)
    x_p[4] = 0.1
    a_p = state_derivative(x_p, u, vehicle)[6:9]
    assert a_p[0] < 0.0
    x_r = np.zeros(12)
    x_r[3] = 0.1
    a_r = state_derivative(x_r, u, vehicle)[6:9]
    assert a_r[1] > 0.0


def test_linearization_matches_finite_difference() -> None:
    """Analytic hover A,B must match FD of nonlinear f at trim."""
    vehicle = default_vehicle()
    x0 = np.zeros(12)
    u0 = vehicle.u_hover()
    a_an, b_an = hover_linearization(vehicle)
    f0 = state_derivative(x0, u0, vehicle)
    eps = 1e-6
    a_fd = np.zeros((12, 12))
    b_fd = np.zeros((12, 4))
    for i in range(12):
        xp = x0.copy()
        xp[i] += eps
        a_fd[:, i] = (state_derivative(xp, u0, vehicle) - f0) / eps
    for j in range(4):
        up = u0.copy()
        up[j] += eps
        b_fd[:, j] = (state_derivative(x0, up, vehicle) - f0) / eps
    np.testing.assert_allclose(a_fd, a_an, atol=2e-4, rtol=0)
    np.testing.assert_allclose(b_fd, b_an, atol=1e-6, rtol=0)


def test_linearization_shapes_and_structure() -> None:
    vehicle = default_vehicle()
    a, b = hover_linearization(vehicle)
    assert a.shape == (12, 12)
    assert b.shape == (12, 4)
    assert a[0, 6] == 1.0
    assert a[6, 4] == -vehicle.gravity_m_s2
    assert a[7, 3] == vehicle.gravity_m_s2
    assert abs(b[8, 0] + 1.0 / vehicle.mass_kg) < 1e-12
