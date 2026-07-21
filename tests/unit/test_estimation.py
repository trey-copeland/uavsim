"""Phase 5d: observers and measurement models."""

from __future__ import annotations

import numpy as np

from uavsim.estimation import (
    IdentityObserver,
    LinearStateKalmanFilter,
    MeasurementModel,
    build_observer,
)
from uavsim.vehicles import default_vehicle


def test_identity_passthrough() -> None:
    obs = IdentityObserver()
    x0 = np.arange(12, dtype=float) * 0.01
    obs.reset(x0)
    y = x0 + 1.0
    np.testing.assert_allclose(obs.update(y), y)
    np.testing.assert_allclose(obs.x_hat, y)


def test_measurement_noise_seed_stable() -> None:
    m1 = MeasurementModel(seed=3, pos_sigma_m=0.1)
    m2 = MeasurementModel(seed=3, pos_sigma_m=0.1)
    x = np.zeros(12)
    y1 = m1.measure(x)
    y2 = m2.measure(x)
    np.testing.assert_allclose(y1, y2)
    assert np.linalg.norm(y1[0:3]) > 0


def test_linear_kf_reduces_static_noise() -> None:
    vehicle = default_vehicle()
    kf = LinearStateKalmanFilter(vehicle, pos_sigma_m=0.2, process_sigma=0.01)
    truth = np.zeros(12)
    truth[2] = 1.0
    kf.reset(truth)
    rng = np.random.default_rng(0)
    errs = []
    for _ in range(40):
        kf.predict(0.02, vehicle.u_hover())
        y = truth.copy()
        y[0:3] += rng.normal(0, 0.2, size=3)
        xh = kf.update(y)
        errs.append(np.linalg.norm(xh[0:3] - truth[0:3]))
    # Later estimates should beat single noisy measurement scale
    assert np.mean(errs[-10:]) < 0.15


def test_build_observer_none_and_kf() -> None:
    vehicle = default_vehicle()
    o1, m1 = build_observer("none", vehicle)
    assert isinstance(o1, IdentityObserver)
    assert m1 is None
    o2, m2 = build_observer(
        {
            "type": "linear_kf",
            "seed": 1,
            "pos_sigma_m": 0.04,
        },
        vehicle,
    )
    assert isinstance(o2, LinearStateKalmanFilter)
    assert m2 is not None
