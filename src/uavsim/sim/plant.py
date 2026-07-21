"""Plant session: dynamics + optional saturation (separable from controller)."""

from __future__ import annotations

from typing import Literal

import numpy as np

from uavsim.control.base import saturate
from uavsim.dynamics import STATE_DIM, STATE_DIM_QUAT, state_derivative, state_derivative_quat
from uavsim.dynamics.nonlinear import (
    euler_state_to_quat_state,
    quat_state_to_euler_state,
    renormalize_quat_state,
)
from uavsim.interfaces import ActuatorCommand, MeasurementBus, PlantOutput
from uavsim.vehicles.params import VehicleParams

AttitudeMode = Literal["euler", "quat"]


class SimPlant:
    """In-process plant. Command source is external (SIL adapter or HIL).

    Controllers always observe **Euler 12-state** measurements. With
    ``attitude=\"quat\"``, the internal state is the 13-state quaternion plant
    and is converted for the measurement bus / exported timeseries.
    """

    def __init__(
        self,
        vehicle: VehicleParams,
        apply_saturation: bool = True,
        *,
        attitude: AttitudeMode = "euler",
    ) -> None:
        if attitude not in ("euler", "quat"):
            msg = f"attitude must be 'euler' or 'quat', got {attitude!r}"
            raise ValueError(msg)
        self.vehicle = vehicle
        self.apply_saturation = apply_saturation
        self.attitude: AttitudeMode = attitude
        self._t = 0.0
        self._x = np.zeros(STATE_DIM_QUAT if attitude == "quat" else STATE_DIM)

    @property
    def state_dim(self) -> int:
        return STATE_DIM_QUAT if self.attitude == "quat" else STATE_DIM

    def reset(self, x0: np.ndarray, t0: float = 0.0) -> PlantOutput:
        self._t = float(t0)
        x0 = np.asarray(x0, dtype=float).reshape(-1)
        if self.attitude == "quat":
            if x0.size == STATE_DIM:
                self._x = euler_state_to_quat_state(x0)
            else:
                self._x = renormalize_quat_state(x0)
        else:
            if x0.size == STATE_DIM_QUAT:
                self._x = quat_state_to_euler_state(x0)
            else:
                self._x = x0.reshape(STATE_DIM).copy()
        return self._output()

    @property
    def t(self) -> float:
        return self._t

    @property
    def x(self) -> np.ndarray:
        """Internal plant state (12 or 13)."""
        return self._x.copy()

    def x_euler(self) -> np.ndarray:
        """Euler 12-state for control / metrics / artifacts."""
        if self.attitude == "quat":
            return quat_state_to_euler_state(self._x)
        return self._x.copy()

    def apply_command(self, command: ActuatorCommand) -> np.ndarray:
        u = command.u
        if self.apply_saturation:
            u = saturate(u, self.vehicle.limits.u_min(), self.vehicle.limits.u_max())
        return u

    def derivatives(self, t: float, x: np.ndarray, u: np.ndarray) -> np.ndarray:
        _ = t
        if self.attitude == "quat":
            return state_derivative_quat(x, u, self.vehicle)
        return state_derivative(x, u, self.vehicle)

    def set_state(self, t: float, x: np.ndarray) -> None:
        self._t = float(t)
        x = np.asarray(x, dtype=float).reshape(-1)
        if self.attitude == "quat":
            self._x = renormalize_quat_state(x)
        else:
            self._x = x.reshape(STATE_DIM).copy()

    def _output(self) -> PlantOutput:
        x_e = self.x_euler()
        return PlantOutput(
            t=self._t,
            x_true=x_e,
            measurements=MeasurementBus(t=self._t, x=x_e),
        )
