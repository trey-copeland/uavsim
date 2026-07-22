"""Unit tests for LQR hover design."""

from __future__ import annotations

import numpy as np

from uavsim.control import design_lqr_hover
from uavsim.interfaces import MeasurementBus
from uavsim.reference import ReferenceSample
from uavsim.vehicles import default_vehicle


def test_lqr_closed_loop_poles_stable() -> None:
    ctrl = design_lqr_hover(default_vehicle())
    assert np.all(np.real(ctrl.poles) < 0)


def test_lqr_at_trim_gives_hover_thrust() -> None:
    vehicle = default_vehicle()
    ctrl = design_lqr_hover(vehicle)
    x = np.zeros(12)
    meas = MeasurementBus(t=0.0, x=x)
    ref = ReferenceSample(t=0.0, x_ref=x)
    u = ctrl.compute(0.0, meas, ref).u
    assert np.allclose(u, vehicle.u_hover(), atol=1e-9)


def test_lqr_opposes_position_error() -> None:
    vehicle = default_vehicle()
    ctrl = design_lqr_hover(vehicle)
    x = np.zeros(12)
    x[0] = 1.0  # north of reference
    meas = MeasurementBus(t=0.0, x=x)
    ref = ReferenceSample(t=0.0, x_ref=np.zeros(12))
    u = ctrl.compute(0.0, meas, ref).u
    # Expect non-trivial corrective action (torques and/or thrust)
    assert np.linalg.norm(u - vehicle.u_hover()) > 1e-6


def test_lqr_corrective_torque_signs() -> None:
    """North error → +pitch torque (→ +θ → −ẍ); east → −roll torque (→ −φ → −ÿ)."""
    vehicle = default_vehicle()
    ctrl = design_lqr_hover(vehicle)
    ref = ReferenceSample(t=0.0, x_ref=np.zeros(12))

    x_n = np.zeros(12)
    x_n[0] = 1.0
    u_n = ctrl.compute(0.0, MeasurementBus(t=0.0, x=x_n), ref).u
    assert u_n[2] > 0.0

    x_e = np.zeros(12)
    x_e[1] = 1.0
    u_e = ctrl.compute(0.0, MeasurementBus(t=0.0, x=x_e), ref).u
    assert u_e[1] < 0.0
