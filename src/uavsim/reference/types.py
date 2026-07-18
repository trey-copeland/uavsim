"""Reference trajectory types (backend-agnostic)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
from scipy.interpolate import interp1d

from uavsim.dynamics.nonlinear import STATE_DIM


@dataclass(frozen=True)
class ReferenceSample:
    """Point sample of a reference trajectory for control / metrics."""

    t: float
    x_ref: np.ndarray  # full 12-state reference for LQR tracking

    def __post_init__(self) -> None:
        object.__setattr__(self, "x_ref", np.asarray(self.x_ref, dtype=float).reshape(STATE_DIM))


@dataclass
class ReferenceTrajectory:
    t0: float
    tf: float
    backend_id: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def evaluate(self, t: float) -> ReferenceSample:
        raise NotImplementedError


@dataclass
class HoldReference(ReferenceTrajectory):
    """Constant full-state setpoint over [t0, tf]."""

    x_hold: np.ndarray = field(default_factory=lambda: np.zeros(STATE_DIM))

    def __post_init__(self) -> None:
        self.x_hold = np.asarray(self.x_hold, dtype=float).reshape(STATE_DIM)

    def evaluate(self, t: float) -> ReferenceSample:
        _ = min(max(t, self.t0), self.tf)
        return ReferenceSample(t=t, x_ref=self.x_hold.copy())


@dataclass
class SampledReference(ReferenceTrajectory):
    """
    Dense-grid reference with linear interpolation of the 12-state signal.

    Position / velocity / attitude / rates are stored on a common time grid and
    evaluated at arbitrary t by clamping to [t0, tf] then interpolating.
    """

    t_grid: np.ndarray = field(default_factory=lambda: np.array([0.0, 1.0]))
    x_grid: np.ndarray = field(default_factory=lambda: np.zeros((2, STATE_DIM)))
    _interp: Any = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        self.t_grid = np.asarray(self.t_grid, dtype=float).reshape(-1)
        self.x_grid = np.asarray(self.x_grid, dtype=float)
        if self.t_grid.ndim != 1 or self.t_grid.size < 2:
            msg = "SampledReference requires t_grid with at least 2 points"
            raise ValueError(msg)
        if self.x_grid.shape != (self.t_grid.size, STATE_DIM):
            msg = f"x_grid must have shape ({self.t_grid.size}, {STATE_DIM})"
            raise ValueError(msg)
        if not np.all(np.diff(self.t_grid) > 0):
            msg = "t_grid must be strictly increasing"
            raise ValueError(msg)
        self.t0 = float(self.t_grid[0])
        self.tf = float(self.t_grid[-1])
        # Linear interp is stable for control; grids are dense (dt ~ 0.01 s).
        self._interp = interp1d(
            self.t_grid,
            self.x_grid,
            axis=0,
            kind="linear",
            bounds_error=False,
            fill_value=(self.x_grid[0], self.x_grid[-1]),
            assume_sorted=True,
        )

    def evaluate(self, t: float) -> ReferenceSample:
        tc = float(np.clip(t, self.t0, self.tf))
        x_ref = np.asarray(self._interp(tc), dtype=float).reshape(STATE_DIM)
        return ReferenceSample(t=t, x_ref=x_ref)


def hold_at_ned(
    position_ned_m: np.ndarray,
    yaw_rad: float = 0.0,
    duration_s: float = 5.0,
    t0: float = 0.0,
) -> HoldReference:
    x = np.zeros(STATE_DIM)
    x[0:3] = np.asarray(position_ned_m, dtype=float).reshape(3)
    x[5] = float(yaw_rad)
    return HoldReference(
        t0=t0,
        tf=t0 + duration_s,
        backend_id="hold",
        metadata={"yaw_rad": yaw_rad, "position_ned_m": list(map(float, x[0:3]))},
        x_hold=x,
    )


def pack_state_grid(
    position_ned: np.ndarray,
    velocity_ned: np.ndarray,
    euler_rad: np.ndarray,
    omega_body: np.ndarray,
) -> np.ndarray:
    """Stack trajectory channels into (N, 12) state grid."""
    n = position_ned.shape[0]
    x = np.zeros((n, STATE_DIM), dtype=float)
    x[:, 0:3] = position_ned
    x[:, 3:6] = euler_rad
    x[:, 6:9] = velocity_ned
    x[:, 9:12] = omega_body
    return x
