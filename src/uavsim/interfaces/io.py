"""Plant I/O contracts (HIL-ready seams)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from uavsim.dynamics.nonlinear import CONTROL_DIM, STATE_DIM


@dataclass(frozen=True)
class ActuatorCommand:
    """Control input to the plant: [F, τφ, τθ, τψ]."""

    u: np.ndarray

    def __post_init__(self) -> None:
        object.__setattr__(self, "u", np.asarray(self.u, dtype=float).reshape(CONTROL_DIM))


@dataclass(frozen=True)
class MeasurementBus:
    """What a controller may observe. Phase 1: ideal full state."""

    t: float
    x: np.ndarray

    def __post_init__(self) -> None:
        object.__setattr__(self, "x", np.asarray(self.x, dtype=float).reshape(STATE_DIM))


@dataclass(frozen=True)
class PlantOutput:
    t: float
    x_true: np.ndarray
    measurements: MeasurementBus
