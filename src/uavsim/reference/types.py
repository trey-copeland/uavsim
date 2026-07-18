"""Reference trajectory types (backend-agnostic)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from uavsim.dynamics.nonlinear import STATE_DIM


@dataclass(frozen=True)
class ReferenceSample:
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
        # Clamp to horizon for sim convenience
        _ = min(max(t, self.t0), self.tf)
        return ReferenceSample(t=t, x_ref=self.x_hold.copy())


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
