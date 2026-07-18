"""Controller protocol."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import numpy as np

from uavsim.interfaces import ActuatorCommand, MeasurementBus
from uavsim.reference import ReferenceSample


@runtime_checkable
class Controller(Protocol):
    id: str

    def compute(
        self,
        t: float,
        measurements: MeasurementBus,
        reference: ReferenceSample,
    ) -> ActuatorCommand:
        """Return actuator command from measurements + reference sample."""
        ...


def saturate(u: np.ndarray, u_min: np.ndarray, u_max: np.ndarray) -> np.ndarray:
    return np.minimum(np.maximum(u, u_min), u_max)
