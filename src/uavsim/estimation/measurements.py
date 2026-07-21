"""Measurement models for observer-in-the-loop SIL (full or partial state)."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from uavsim.dynamics import STATE_DIM
from uavsim.estimation.channels import (
    DEFAULT_CHANNELS,
    channel_indices,
    measurement_noise_diag,
    normalize_channels,
    pack_measurement,
    selection_matrix,
)


@dataclass
class Observation:
    """Partial or full measurement with selection matrix H (m×12)."""

    y: np.ndarray
    h: np.ndarray
    r: np.ndarray
    channels: list[str]


@dataclass
class MeasurementModel:
    """
    Additive Gaussian noise on selected Euler 12-state channels.

    ``channels`` defaults to full state. Use e.g. ``[\"pos\", \"omega\"]`` for
    GPS-like position + gyro-only partial sensing.
    """

    seed: int = 0
    pos_sigma_m: float = 0.0
    vel_sigma_m_s: float = 0.0
    att_sigma_rad: float = 0.0
    omega_sigma_rad_s: float = 0.0
    channels: list[str] = field(default_factory=lambda: list(DEFAULT_CHANNELS))

    def __post_init__(self) -> None:
        self.channels = normalize_channels(self.channels)
        self._rng = np.random.default_rng(int(self.seed))
        self._idx = channel_indices(self.channels)
        self._h = selection_matrix(self.channels)
        self._r_diag = measurement_noise_diag(
            self.channels,
            pos_sigma_m=self.pos_sigma_m,
            vel_sigma_m_s=self.vel_sigma_m_s,
            att_sigma_rad=self.att_sigma_rad,
            omega_sigma_rad_s=self.omega_sigma_rad_s,
        )

    def measure(self, x_true_euler: np.ndarray) -> np.ndarray:
        """Return noisy **full** 12-state (unmeasured channels = true, no noise)."""
        x = np.asarray(x_true_euler, dtype=float).reshape(STATE_DIM).copy()
        y_part = self.measure_vector(x)
        x[self._idx] = y_part
        return x

    def measure_vector(self, x_true_euler: np.ndarray) -> np.ndarray:
        """Noisy measurement vector y (length m) for selected channels only."""
        y = pack_measurement(x_true_euler, self.channels)
        noise = self._rng.normal(0.0, 1.0, size=y.size) * np.sqrt(self._r_diag)
        return y + noise

    def observe(self, x_true_euler: np.ndarray) -> Observation:
        y = self.measure_vector(x_true_euler)
        return Observation(
            y=y,
            h=self._h.copy(),
            r=np.diag(self._r_diag),
            channels=list(self.channels),
        )


def apply_measurement_noise(
    x_true_euler: np.ndarray,
    model: MeasurementModel | None,
) -> np.ndarray:
    """Back-compat: return full 12-state with noise on configured channels."""
    if model is None:
        return np.asarray(x_true_euler, dtype=float).reshape(STATE_DIM).copy()
    return model.measure(x_true_euler)
