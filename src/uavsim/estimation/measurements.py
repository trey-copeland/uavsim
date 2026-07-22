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
    Additive Gaussian noise on selected measurement channels.

    Channels may be Euler slices (``pos``, ``att``, ``vel``, ``omega``),
    altitude (``alt``), horizontal velocity (``vel_xy``), or body-frame
    velocity / optical-flow proxy (``body_vel`` / ``flow``).
    """

    seed: int = 0
    pos_sigma_m: float = 0.0
    vel_sigma_m_s: float = 0.0
    att_sigma_rad: float = 0.0
    omega_sigma_rad_s: float = 0.0
    alt_sigma_m: float | None = None
    body_vel_sigma_m_s: float | None = None
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
            alt_sigma_m=self.alt_sigma_m,
            body_vel_sigma_m_s=self.body_vel_sigma_m_s,
        )

    def measure(self, x_true_euler: np.ndarray) -> np.ndarray:
        """
        Return noisy **full** 12-state for legacy paths.

        Unmeasured channels keep truth. ``body_vel`` is packed into NED vel
        slots (hover-linear / partial_raw bus convention).
        """
        x = np.asarray(x_true_euler, dtype=float).reshape(STATE_DIM).copy()
        y_part = self.measure_vector(x)
        # Place via H columns (works for selection and body_vel hover H)
        h = self._h
        for i in range(h.shape[0]):
            js = np.flatnonzero(np.abs(h[i]) > 0.5)
            if js.size == 1:
                x[int(js[0])] = y_part[i]
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
