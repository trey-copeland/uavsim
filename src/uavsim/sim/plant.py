"""Plant session: dynamics + optional saturation (separable from controller)."""

from __future__ import annotations

from typing import Literal

import numpy as np

from uavsim.control.base import saturate
from uavsim.dynamics import STATE_DIM, STATE_DIM_QUAT
from uavsim.dynamics.mixer import N_MOTORS, hover_omega
from uavsim.dynamics.model import DynamicsModel, PlantKind, get_dynamics_model
from uavsim.interfaces import ActuatorCommand, MeasurementBus, PlantOutput
from uavsim.vehicles.params import VehicleParams

AttitudeMode = Literal["euler", "quat"]


class SimPlant:
    """In-process plant. Command source is external (SIL adapter or HIL).

    Controllers always observe **Euler 12-state** measurements. Plant state
    dimension and kinematics come from a :class:`DynamicsModel` (D-3).
    """

    def __init__(
        self,
        vehicle: VehicleParams,
        apply_saturation: bool = True,
        *,
        attitude: AttitudeMode = "euler",
        plant: PlantKind = "wrench",
        dynamics: DynamicsModel | None = None,
    ) -> None:
        self.vehicle = vehicle
        self.apply_saturation = apply_saturation
        self.plant_kind: PlantKind = plant
        self.dynamics: DynamicsModel = (
            dynamics if dynamics is not None else get_dynamics_model(attitude, plant=plant)
        )
        self.attitude: AttitudeMode = self.dynamics.attitude  # type: ignore[assignment]
        self._t = 0.0
        self._x = np.zeros(self.dynamics.state_dim)

    @property
    def state_dim(self) -> int:
        return self.dynamics.state_dim

    def reset(self, x0: np.ndarray, t0: float = 0.0) -> PlantOutput:
        self._t = float(t0)
        x0 = np.asarray(x0, dtype=float).reshape(-1)
        if x0.size == self.dynamics.state_dim:
            self._x = self.dynamics.project(x0)
        elif x0.size == STATE_DIM:
            self._x = self._from_euler_with_motors(x0)
        elif x0.size == STATE_DIM_QUAT and self.dynamics.attitude == "euler":
            from uavsim.dynamics.nonlinear import quat_state_to_euler_state

            self._x = self._from_euler_with_motors(quat_state_to_euler_state(x0))
        else:
            msg = (
                f"x0 length {x0.size} incompatible with dynamics "
                f"{self.dynamics.id} (dim={self.dynamics.state_dim})"
            )
            raise ValueError(msg)
        return self._output()

    def _from_euler_with_motors(self, x_euler: np.ndarray) -> np.ndarray:
        """Map Euler 12-state into plant state; motors start at hover ω when present."""
        x = self.dynamics.from_euler_state(x_euler)
        if x.size == STATE_DIM + N_MOTORS or x.size == STATE_DIM_QUAT + N_MOTORS:
            w0 = hover_omega(self.vehicle)
            x = x.copy()
            x[-N_MOTORS:] = w0
        return self.dynamics.project(x)

    @property
    def t(self) -> float:
        return self._t

    @property
    def x(self) -> np.ndarray:
        """Internal plant state."""
        return self._x.copy()

    def x_euler(self) -> np.ndarray:
        """Euler 12-state for control / metrics / artifacts."""
        return self.dynamics.to_euler_state(self._x)

    def apply_command(self, command: ActuatorCommand) -> np.ndarray:
        u = command.u
        if self.apply_saturation:
            u = saturate(u, self.vehicle.limits.u_min(), self.vehicle.limits.u_max())
        return u

    def derivatives(self, t: float, x: np.ndarray, u: np.ndarray) -> np.ndarray:
        _ = t
        return self.dynamics.f(x, u, self.vehicle)

    def set_state(self, t: float, x: np.ndarray) -> None:
        self._t = float(t)
        self._x = self.dynamics.project(x)

    def _output(self) -> PlantOutput:
        x_e = self.x_euler()
        return PlantOutput(
            t=self._t,
            x_true=x_e,
            measurements=MeasurementBus(t=self._t, x=x_e),
        )
