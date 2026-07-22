"""GPS-denied channels: body_vel (flow), alt, vel_xy."""

from __future__ import annotations

import numpy as np

from uavsim.dynamics.rotations import rotation_body_to_inertial
from uavsim.estimation.channels import (
    measurement_dim,
    normalize_channels,
    pack_measurement,
    selection_matrix,
)
from uavsim.estimation.factory import build_observer
from uavsim.estimation.measurements import MeasurementModel
from uavsim.vehicles import default_vehicle


def test_normalize_flow_aliases() -> None:
    assert normalize_channels(["flow", "altitude", "gyro"]) == ["body_vel", "alt", "omega"]


def test_body_vel_is_r_transpose_v() -> None:
    x = np.zeros(12)
    x[3:6] = [0.1, -0.05, 0.2]
    x[6:9] = [1.0, 0.5, -0.2]
    y = pack_measurement(x, ["body_vel"])
    r = rotation_body_to_inertial(0.1, -0.05, 0.2)
    np.testing.assert_allclose(y, r.T @ x[6:9], atol=1e-12)


def test_alt_and_dims() -> None:
    x = np.zeros(12)
    x[2] = 1.25
    y = pack_measurement(x, ["alt", "vel_xy"])
    np.testing.assert_allclose(y, [1.25, 0.0, 0.0])
    assert measurement_dim(["body_vel", "alt", "omega"]) == 7


def test_selection_h_body_vel_hover() -> None:
    h = selection_matrix(["body_vel", "alt", "omega"])
    assert h.shape == (7, 12)
    # body_vel → NED vel rows
    np.testing.assert_allclose(h[0:3, 6:9], np.eye(3))
    assert h[3, 2] == 1.0
    np.testing.assert_allclose(h[4:7, 9:12], np.eye(3))


def test_measurement_observe_flow_stack() -> None:
    m = MeasurementModel(
        seed=1,
        channels=["body_vel", "alt", "omega"],
        vel_sigma_m_s=0.05,
        alt_sigma_m=0.02,
        omega_sigma_rad_s=0.01,
        body_vel_sigma_m_s=0.05,
    )
    x = np.zeros(12)
    x[2] = 1.0
    x[6] = 0.3
    obs = m.observe(x)
    assert obs.y.shape == (7,)
    assert obs.h.shape == (7, 12)
    assert obs.channels == ["body_vel", "alt", "omega"]


def test_flow_alt_kf_builds_and_tracks_hover() -> None:
    vehicle = default_vehicle()
    obs, meas = build_observer(
        {
            "type": "linear_kf",
            "seed": 0,
            "channels": ["body_vel", "alt", "omega"],
            "vel_sigma_m_s": 0.05,
            "alt_sigma_m": 0.03,
            "omega_sigma_rad_s": 0.02,
            "process_sigma": 0.02,
        },
        vehicle,
    )
    assert meas is not None
    x = np.zeros(12)
    x[2] = 1.0
    obs.reset(x)
    for _ in range(30):
        obs.predict(0.01, vehicle.u_hover())
        obs.update(meas.observe(x))
    # Altitude channel should pin z
    assert abs(obs.x_hat[2] - 1.0) < 0.15
