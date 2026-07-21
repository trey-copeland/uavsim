"""Measurement channel layout for partial-state observers (Phase 5d stretch)."""

from __future__ import annotations

from collections.abc import Iterable, Sequence

import numpy as np

from uavsim.dynamics import STATE_DIM

# Named blocks on the Euler 12-state
CHANNEL_SLICES: dict[str, slice] = {
    "pos": slice(0, 3),
    "att": slice(3, 6),
    "vel": slice(6, 9),
    "omega": slice(9, 12),
}

CHANNEL_ALIASES: dict[str, str] = {
    "position": "pos",
    "attitude": "att",
    "velocity": "vel",
    "rate": "omega",
    "gyro": "omega",
    "p": "pos",
    "v": "vel",
    "w": "omega",
}

DEFAULT_CHANNELS: tuple[str, ...] = ("pos", "att", "vel", "omega")


def normalize_channels(channels: Sequence[str] | None) -> list[str]:
    if not channels:
        return list(DEFAULT_CHANNELS)
    out: list[str] = []
    for c in channels:
        key = CHANNEL_ALIASES.get(c.lower(), c.lower())
        if key not in CHANNEL_SLICES:
            msg = f"Unknown measurement channel {c!r}; known: {sorted(CHANNEL_SLICES)}"
            raise ValueError(msg)
        if key not in out:
            out.append(key)
    return out


def channel_indices(channels: Sequence[str] | None) -> np.ndarray:
    """Row indices into the 12-state for the selected channels."""
    ch = normalize_channels(channels)
    idx: list[int] = []
    for name in ch:
        s = CHANNEL_SLICES[name]
        idx.extend(range(s.start, s.stop))
    return np.asarray(idx, dtype=int)


def selection_matrix(channels: Sequence[str] | None) -> np.ndarray:
    """H (m×12) selecting measured channels."""
    idx = channel_indices(channels)
    h = np.zeros((idx.size, STATE_DIM))
    for i, j in enumerate(idx):
        h[i, j] = 1.0
    return h


def pack_measurement(x_euler: np.ndarray, channels: Sequence[str] | None) -> np.ndarray:
    """Extract y = H x from a full Euler state."""
    x = np.asarray(x_euler, dtype=float).reshape(STATE_DIM)
    return x[channel_indices(channels)].copy()


def measurement_noise_diag(
    channels: Sequence[str] | None,
    *,
    pos_sigma_m: float,
    vel_sigma_m_s: float,
    att_sigma_rad: float,
    omega_sigma_rad_s: float,
) -> np.ndarray:
    """Diagonal R entries matching channel order."""
    sig = {
        "pos": max(pos_sigma_m, 1e-9),
        "att": max(att_sigma_rad, 1e-9),
        "vel": max(vel_sigma_m_s, 1e-9),
        "omega": max(omega_sigma_rad_s, 1e-9),
    }
    diags: list[float] = []
    for name in normalize_channels(channels):
        diags.extend([sig[name] ** 2] * 3)
    return np.asarray(diags, dtype=float)


def validate_channel_list(channels: Iterable[str]) -> list[str]:
    return normalize_channels(list(channels))
