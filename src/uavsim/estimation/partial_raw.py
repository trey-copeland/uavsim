"""Naive partial-state feedback: measured channels only, zeros elsewhere."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from uavsim.dynamics import STATE_DIM
from uavsim.estimation.channels import channel_indices, normalize_channels
from uavsim.estimation.measurements import Observation


class PartialRawObserver:
    """
    No dynamics / no fusion: pack noisy measurements into a 12-state bus.

    Unmeasured channels are **zero** (strong teaching baseline vs a KF that
    reconstructs full state from partial sensors).
    """

    id = "partial_raw"

    def __init__(self, channels: Sequence[str] | None = None) -> None:
        self.channels = normalize_channels(channels)
        self._idx = channel_indices(self.channels)
        self._x = np.zeros(STATE_DIM)
        self._t = 0.0

    def reset(self, x0: np.ndarray, t0: float = 0.0) -> None:
        # Start with zeros on unmeasured channels even if x0 is full truth —
        # first update will fill measured slots. Keep measured from x0 only if
        # we have not yet seen a measurement (open-loop init).
        x0 = np.asarray(x0, dtype=float).reshape(STATE_DIM)
        self._x = np.zeros(STATE_DIM)
        self._x[self._idx] = x0[self._idx]
        self._t = float(t0)

    def predict(self, dt: float, u: np.ndarray) -> np.ndarray:
        _ = dt, u
        return self._x.copy()

    def update(self, y: np.ndarray | Observation) -> np.ndarray:
        self._x = np.zeros(STATE_DIM)
        if isinstance(y, Observation):
            y_vec = np.asarray(y.y, dtype=float).reshape(-1)
            h = np.asarray(y.h, dtype=float)
            # y = H x  →  place components via H columns (unit rows)
            if h.shape[0] != y_vec.size:
                msg = f"Observation y size {y_vec.size} != H rows {h.shape[0]}"
                raise ValueError(msg)
            # For selection matrices, H[i,j]=1 maps y[i] → x[j]
            for i in range(h.shape[0]):
                js = np.flatnonzero(h[i])
                if js.size == 1:
                    self._x[int(js[0])] = y_vec[i]
                elif js.size > 1:
                    # unexpected dense row — least-squares place
                    self._x += h[i] * y_vec[i]
        else:
            y_arr = np.asarray(y, dtype=float).reshape(-1)
            if y_arr.size == STATE_DIM:
                self._x[self._idx] = y_arr[self._idx]
            elif y_arr.size == self._idx.size:
                self._x[self._idx] = y_arr
            else:
                msg = f"y length {y_arr.size} incompatible with channels {self.channels}"
                raise ValueError(msg)
        return self._x.copy()

    @property
    def x_hat(self) -> np.ndarray:
        return self._x.copy()
