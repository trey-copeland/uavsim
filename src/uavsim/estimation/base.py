"""Observer protocol for plant → estimate → controller (Phase 5d)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import numpy as np


@runtime_checkable
class StateObserver(Protocol):
    """Discrete-time state observer operating on Euler 12-state estimates."""

    id: str

    def reset(self, x0: np.ndarray, t0: float = 0.0) -> None:
        """Initialize estimate (typically from true or nominal state)."""
        ...

    def predict(self, dt: float, u: np.ndarray) -> np.ndarray:
        """Time update; returns current estimate after prediction."""
        ...

    def update(self, y: np.ndarray) -> np.ndarray:
        """Measurement update; ``y`` is same layout as Euler 12-state (or as documented)."""
        ...

    @property
    def x_hat(self) -> np.ndarray:
        """Current Euler 12-state estimate."""
        ...
