"""Feedforward roll/pitch must match plant tilt→accel (NED / −body-z thrust)."""

from __future__ import annotations

import numpy as np

from uavsim.dynamics import state_derivative
from uavsim.reference.attitude import feedforward_roll_pitch
from uavsim.vehicles import default_vehicle


def test_feedforward_signs_match_plant() -> None:
    """Desired +a_x / +a_y → plant acceleration in the same direction at FF attitude."""
    vehicle = default_vehicle()
    g = vehicle.gravity_m_s2
    cases = [
        np.array([2.0, 0.0, 0.0]),
        np.array([0.0, 2.0, 0.0]),
        np.array([1.5, -1.0, 0.0]),
        np.array([-1.0, 0.5, 0.0]),
        np.array([2.5, 2.5, 0.0]),
    ]
    for a_des in cases:
        phi, theta = feedforward_roll_pitch(a_des, g=g)
        x = np.zeros(12)
        x[3] = float(np.asarray(phi).reshape(-1)[0])
        x[4] = float(np.asarray(theta).reshape(-1)[0])
        a_plant = state_derivative(x, vehicle.u_hover(), vehicle)[6:9]
        # Exact hover-thrust inversion → machine-precision match (unclipped)
        np.testing.assert_allclose(a_plant[0], a_des[0], atol=1e-10)
        np.testing.assert_allclose(a_plant[1], a_des[1], atol=1e-10)


def test_feedforward_matches_small_angle_linearization() -> None:
    g = 9.81
    ax, ay = 1.0, -0.5
    phi, theta = feedforward_roll_pitch(np.array([ax, ay, 0.0]), g=g)
    # θ ≈ -a_x/g, φ ≈ a_y/g
    np.testing.assert_allclose(float(np.asarray(theta).reshape(-1)[0]), -ax / g, atol=0.02)
    np.testing.assert_allclose(float(np.asarray(phi).reshape(-1)[0]), ay / g, atol=0.02)


def test_feedforward_clip_respects_max_tilt() -> None:
    g = 9.81
    max_tilt = np.deg2rad(20.0)
    # Huge accel request — horizontal accel clipped to g·sin(max_tilt)
    a_req = np.array([50.0, 50.0, 0.0])
    phi, theta = feedforward_roll_pitch(a_req, g=g, max_tilt_rad=max_tilt)
    # Each Euler angle stays within the tilt budget (not hypot of angles)
    assert abs(float(phi[0])) <= max_tilt + 1e-6
    assert abs(float(theta[0])) <= max_tilt + 1e-6
    # Plant horizontal accel magnitude stays ≤ g sin(max_tilt)
    from uavsim.dynamics import state_derivative
    from uavsim.vehicles import default_vehicle

    vehicle = default_vehicle()
    x = np.zeros(12)
    x[3] = float(phi[0])
    x[4] = float(theta[0])
    a = state_derivative(x, vehicle.u_hover(), vehicle)[6:9]
    assert float(np.hypot(a[0], a[1])) <= g * np.sin(max_tilt) + 0.05
