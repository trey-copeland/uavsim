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


def test_linearization_shapes_and_structure() -> None:
    vehicle = default_vehicle()
    a, b = hover_linearization(vehicle)
    assert a.shape == (12, 12)
    assert b.shape == (12, 4)
    assert a[0, 6] == 1.0
    assert a[6, 4] == -vehicle.gravity_m_s2
    assert a[7, 3] == vehicle.gravity_m_s2
    assert abs(b[8, 0] + 1.0 / vehicle.mass_kg) < 1e-12
