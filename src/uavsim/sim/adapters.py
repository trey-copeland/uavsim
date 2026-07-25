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
        # Last sample passed to the controller (for metrics under online replan).
        self.last_sample: ReferenceSample | None = None

    def set_reference(self, reference: ReferenceTrajectory) -> None:
        """Rebind trajectory after online guidance replan (G-6)."""
        self.reference = reference

    def command(self, t: float, measurements: MeasurementBus) -> ActuatorCommand:
        ref: ReferenceSample = self.reference.evaluate(t)
        self.last_sample = ref
        return self.controller.compute(t, measurements, ref)
