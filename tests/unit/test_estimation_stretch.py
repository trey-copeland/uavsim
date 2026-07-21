"""Phase 5d stretch: partial H, MEKF, channels."""

from __future__ import annotations

import numpy as np

from uavsim.estimation import (
    ErrorStateMekf,
    LinearStateKalmanFilter,
    MeasurementModel,
    build_observer,
)
from uavsim.estimation.channels import selection_matrix
from uavsim.vehicles import default_vehicle


def test_partial_h_shape() -> None:
    h = selection_matrix(["pos", "omega"])
    assert h.shape == (6, 12)
    assert h[0, 0] == 1.0
    assert h[3, 9] == 1.0


def test_linear_kf_partial_channels_update() -> None:
    vehicle = default_vehicle()
    kf = LinearStateKalmanFilter(
        vehicle,
        channels=["pos", "omega"],
        pos_sigma_m=0.1,
        omega_sigma_rad_s=0.05,
    )
    x0 = np.zeros(12)
    x0[2] = 1.0
    kf.reset(x0)
    meas = MeasurementModel(
        seed=1,
        pos_sigma_m=0.1,
        omega_sigma_rad_s=0.05,
        channels=["pos", "omega"],
    )
    for _ in range(20):
        kf.predict(0.02, vehicle.u_hover())
        obs = meas.observe(x0)
        assert obs.y.size == 6
        kf.update(obs)
    assert np.isfinite(kf.x_hat).all()


def test_mekf_tracks_hover_with_noise() -> None:
    vehicle = default_vehicle()
    filt = ErrorStateMekf(vehicle, channels=["pos", "att", "omega"], process_sigma=0.01)
    truth = np.zeros(12)
    truth[2] = 1.0
    filt.reset(truth)
    meas = MeasurementModel(
        seed=2,
        pos_sigma_m=0.05,
        att_sigma_rad=0.02,
        omega_sigma_rad_s=0.02,
        channels=["pos", "att", "omega"],
    )
    for _ in range(30):
        filt.predict(0.02, vehicle.u_hover())
        filt.update(meas.observe(truth))
    xh = filt.x_hat
    assert abs(xh[2] - 1.0) < 0.15
    assert np.linalg.norm(xh[3:6]) < 0.2


def test_build_mekf_and_partial() -> None:
    vehicle = default_vehicle()
    o, m = build_observer(
        {
            "type": "mekf",
            "seed": 0,
            "channels": ["pos", "omega"],
            "pos_sigma_m": 0.05,
        },
        vehicle,
    )
    assert isinstance(o, ErrorStateMekf)
    assert m is not None
    assert m.channels == ["pos", "omega"]
