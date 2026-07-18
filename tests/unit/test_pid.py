"""PID cascade unit tests."""

from __future__ import annotations

import numpy as np

from uavsim.control import design_pid_cascade
from uavsim.interfaces import MeasurementBus
from uavsim.reference import ReferenceSample
from uavsim.vehicles.params import default_vehicle


def test_pid_hover_command_near_mg() -> None:
    vehicle = default_vehicle()
    ctrl = design_pid_cascade(vehicle)
    x = np.zeros(12)
    ref = ReferenceSample(t=0.0, x_ref=np.zeros(12))
    bus = MeasurementBus(t=0.0, x=x)
    u = ctrl.compute(0.0, bus, ref).u
    assert abs(u[0] - vehicle.hover_thrust_n()) < 0.5
    assert np.linalg.norm(u[1:4]) < 0.5


def test_pid_pushes_toward_reference() -> None:
    vehicle = default_vehicle()
    ctrl = design_pid_cascade(vehicle)
    x = np.zeros(12)
    x[0] = 1.0  # north of target → need south accel → +theta (plant: +θ → −ẍ)
    xref = np.zeros(12)
    ref = ReferenceSample(t=0.0, x_ref=xref)
    bus = MeasurementBus(t=0.0, x=x)
    u = ctrl.compute(0.0, bus, ref).u
    assert np.isfinite(u).all()
    # Positive pitch torque initially toward +theta demand
    assert u[2] > 0.0
