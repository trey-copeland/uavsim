"""Plant session: dynamics + optional saturation (separable from controller)."""

from __future__ import annotations

import numpy as np

from uavsim.control.base import saturate
from uavsim.dynamics import STATE_DIM, state_derivative
from uavsim.interfaces import ActuatorCommand, MeasurementBus, PlantOutput
from uavsim.vehicles.params import VehicleParams


class SimPlant:
    """In-process plant. Command source is external (SIL adapter or HIL)."""

    def __init__(self, vehicle: VehicleParams, apply_saturation: bool = True) -> None:
        self.vehicle = vehicle
        self.apply_saturation = apply_saturation
        self._t = 0.0
        self._x = np.zeros(STATE_DIM)

    def reset(self, x0: np.ndarray, t0: float = 0.0) -> PlantOutput:
        self._t = float(t0)
        self._x = np.asarray(x0, dtype=float).reshape(STATE_DIM).copy()
        return self._output()

    @property
    def t(self) -> float:
        return self._t

    @property
    def x(self) -> np.ndarray:
        return self._x.copy()

    def apply_command(self, command: ActuatorCommand) -> np.ndarray:
        u = command.u
        if self.apply_saturation:
            u = saturate(u, self.vehicle.limits.u_min(), self.vehicle.limits.u_max())
        return u

    def derivatives(self, t: float, x: np.ndarray, u: np.ndarray) -> np.ndarray:
        _ = t
        return state_derivative(x, u, self.vehicle)

    def _output(self) -> PlantOutput:
        x = self._x.copy()
        return PlantOutput(
            t=self._t,
            x_true=x,
            measurements=MeasurementBus(t=self._t, x=x),
        )
