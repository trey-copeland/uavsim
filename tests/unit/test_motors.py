"""First-order motor plant (D-7)."""

from __future__ import annotations

import numpy as np

from uavsim.dynamics import EulerMotorDynamics, get_dynamics_model, hover_omega
from uavsim.dynamics.mixer import motor_forces_to_wrench, omega_to_forces
from uavsim.sim.plant import SimPlant
from uavsim.vehicles import default_vehicle


def test_motor_model_dims() -> None:
    m = get_dynamics_model("euler", plant="motors")
    assert m.state_dim == 16
    assert m.id == "euler_motors"
    mq = get_dynamics_model("quat", plant="motors")
    assert mq.state_dim == 17


def test_hover_equilibrium_motor_plant() -> None:
    """At hover ω and u_hover, rigid-body accel ~0 and ω̇ ~0."""
    v = default_vehicle()
    model = EulerMotorDynamics()
    w0 = hover_omega(v)
    x = np.zeros(16)
    x[12:16] = w0
    u = v.u_hover()
    xdot = model.f(x, u, v)
    # vertical accel and motor rates near zero
    assert abs(xdot[8]) < 1e-6
    np.testing.assert_allclose(xdot[12:16], 0.0, atol=1e-5)


def test_motor_lag_responds_to_step() -> None:
    v = default_vehicle()
    model = EulerMotorDynamics()
    w0 = hover_omega(v)
    x = np.zeros(16)
    x[12:16] = w0
    # command more thrust
    u = v.u_hover() * 1.2
    xdot = model.f(x, u, v)
    assert np.all(xdot[12:16] > 0)


def test_plant_reset_inits_hover_motors() -> None:
    v = default_vehicle()
    plant = SimPlant(v, plant="motors", attitude="euler")
    plant.reset(np.zeros(12))
    assert plant.state_dim == 16
    w = plant.x[12:16]
    np.testing.assert_allclose(w, hover_omega(v), rtol=1e-6)
    # realized wrench at init ≈ hover
    f = omega_to_forces(w, v.propulsion)
    u = motor_forces_to_wrench(f, v)
    np.testing.assert_allclose(u[0], v.hover_thrust_n(), rtol=1e-5)
