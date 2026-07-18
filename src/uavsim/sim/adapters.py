"""Command sources for the plant (SIL now; HIL later)."""

from __future__ import annotations

from typing import Protocol

from uavsim.control.base import Controller
from uavsim.interfaces import ActuatorCommand, MeasurementBus
from uavsim.reference import ReferenceSample, ReferenceTrajectory


class CommandSource(Protocol):
    def command(self, t: float, measurements: MeasurementBus) -> ActuatorCommand: ...


class InProcessControllerAdapter:
    """SIL: evaluate reference + in-process Controller → ActuatorCommand."""

    def __init__(self, controller: Controller, reference: ReferenceTrajectory) -> None:
        self.controller = controller
        self.reference = reference

    def command(self, t: float, measurements: MeasurementBus) -> ActuatorCommand:
        ref: ReferenceSample = self.reference.evaluate(t)
        return self.controller.compute(t, measurements, ref)
