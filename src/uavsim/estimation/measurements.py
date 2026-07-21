"""Measurement models for observer-in-the-loop SIL."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from uavsim.dynamics import STATE_DIM


@dataclass
class MeasurementModel:
    """
    Additive Gaussian noise on Euler 12-state channels (independent).

    Zero sigmas → perfect measurements (still useful as a structural hook).
    """

    seed: int = 0
    pos_sigma_m: float = 0.0
    vel_sigma_m_s: float = 0.0
    att_sigma_rad: float = 0.0
    omega_sigma_rad_s: float = 0.0

    def __post_init__(self) -> None:
        self._rng = np.random.default_rng(int(self.seed))

    def measure(self, x_true_euler: np.ndarray) -> np.ndarray:
        x = np.asarray(x_true_euler, dtype=float).reshape(STATE_DIM).copy()
        if self.pos_sigma_m > 0:
            x[0:3] += self._rng.normal(0.0, self.pos_sigma_m, size=3)
        if self.att_sigma_rad > 0:
            x[3:6] += self._rng.normal(0.0, self.att_sigma_rad, size=3)
        if self.vel_sigma_m_s > 0:
            x[6:9] += self._rng.normal(0.0, self.vel_sigma_m_s, size=3)
        if self.omega_sigma_rad_s > 0:
            x[9:12] += self._rng.normal(0.0, self.omega_sigma_rad_s, size=3)
        return x


def apply_measurement_noise(
    x_true_euler: np.ndarray,
    model: MeasurementModel | None,
) -> np.ndarray:
    if model is None:
        return np.asarray(x_true_euler, dtype=float).reshape(STATE_DIM).copy()
    return model.measure(x_true_euler)
