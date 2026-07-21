"""DynamicsModel protocol (Phase 5c.4 / D-3)."""

from __future__ import annotations

import numpy as np

from uavsim.dynamics import (
    DynamicsModel,
    EulerRigidBodyDynamics,
    QuatRigidBodyDynamics,
    get_dynamics_model,
    state_derivative,
    state_derivative_quat,
)
from uavsim.vehicles import default_vehicle


def test_factory_and_protocol() -> None:
    e = get_dynamics_model("euler")
    q = get_dynamics_model("quat")
    assert isinstance(e, DynamicsModel)
    assert isinstance(q, DynamicsModel)
    assert e.state_dim == 12
    assert q.state_dim == 13
    assert e.attitude == "euler"
    assert q.attitude == "quat"


def test_euler_model_matches_state_derivative() -> None:
    vehicle = default_vehicle()
    model = EulerRigidBodyDynamics()
    x = np.zeros(12)
    x[3:6] = [0.05, -0.02, 0.1]
    u = vehicle.u_hover()
    np.testing.assert_allclose(model.f(x, u, vehicle), state_derivative(x, u, vehicle))
    np.testing.assert_allclose(model.to_euler_state(x), x)
    np.testing.assert_allclose(model.from_euler_state(x), x)


def test_quat_model_matches_state_derivative_quat() -> None:
    vehicle = default_vehicle()
    model = QuatRigidBodyDynamics()
    x = np.zeros(13)
    x[3] = 1.0
    u = vehicle.u_hover()
    np.testing.assert_allclose(model.f(x, u, vehicle), state_derivative_quat(x, u, vehicle))
    x_bad = x.copy()
    x_bad[3:7] = [2.0, 0.0, 0.0, 0.0]
    n = np.linalg.norm(model.project(x_bad)[3:7])
    assert abs(n - 1.0) < 1e-12
