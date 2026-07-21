"""Pass-through observer (full-state SIL default)."""

from __future__ import annotations

import numpy as np

from uavsim.dynamics import STATE_DIM


class IdentityObserver:
    """Estimate = last measurement (or x0); no dynamics, no noise filtering."""

    id = "none"

    def __init__(self) -> None:
        self._x = np.zeros(STATE_DIM)
        self._t = 0.0

    def reset(self, x0: np.ndarray, t0: float = 0.0) -> None:
        self._x = np.asarray(x0, dtype=float).reshape(STATE_DIM).copy()
        self._t = float(t0)

    def predict(self, dt: float, u: np.ndarray) -> np.ndarray:
        _ = dt, u
        return self._x.copy()

    def update(self, y: np.ndarray) -> np.ndarray:
        self._x = np.asarray(y, dtype=float).reshape(STATE_DIM).copy()
        return self._x.copy()

    @property
    def x_hat(self) -> np.ndarray:
        return self._x.copy()
