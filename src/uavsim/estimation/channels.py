"""Measurement channel layout for partial-state observers (Phase 5d + GPS-denied).

Linear channels select Euler 12-state slices. ``body_vel`` / ``flow`` measures
body-frame velocity R^T v (optical-flow proxy). ``alt`` is NED z only
(rangefinder / baro stand-in with z positive down).
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

import numpy as np

from uavsim.dynamics import STATE_DIM
from uavsim.dynamics.rotations import rotation_body_to_inertial

# Named blocks on the Euler 12-state (pure selection)
CHANNEL_SLICES: dict[str, slice] = {
    "pos": slice(0, 3),
    "att": slice(3, 6),
    "vel": slice(6, 9),
    "omega": slice(9, 12),
}

# Non-slice / partial channels (dims + semantics)
# body_vel: nonlinear y = R^T v; KF H uses hover-linear ≈ NED vel
SPECIAL_CHANNEL_DIM: dict[str, int] = {
    "alt": 1,  # NED z only
    "vel_xy": 2,  # NED north/east velocity
    "body_vel": 3,  # body-frame velocity (optical flow proxy)
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
    # GPS-denied / altitude / flow
    "z": "alt",
    "height": "alt",
    "altitude": "alt",
    "range": "alt",
    "rangefinder": "alt",
    "v_xy": "vel_xy",
    "vel_ne": "vel_xy",
    "flow": "body_vel",
    "optical_flow": "body_vel",
    "of": "body_vel",
    "v_body": "body_vel",
    "body_velocity": "body_vel",
}

DEFAULT_CHANNELS: tuple[str, ...] = ("pos", "att", "vel", "omega")

_KNOWN = set(CHANNEL_SLICES) | set(SPECIAL_CHANNEL_DIM)


def normalize_channels(channels: Sequence[str] | None) -> list[str]:
    if not channels:
        return list(DEFAULT_CHANNELS)
    out: list[str] = []
    for c in channels:
        key = CHANNEL_ALIASES.get(c.lower(), c.lower())
        if key not in _KNOWN:
            msg = f"Unknown measurement channel {c!r}; known: {sorted(_KNOWN)}"
            raise ValueError(msg)
        if key not in out:
            out.append(key)
    return out


def channel_dim(name: str) -> int:
    """Number of scalar measurements for one named channel."""
    key = CHANNEL_ALIASES.get(name.lower(), name.lower())
    if key in CHANNEL_SLICES:
        s = CHANNEL_SLICES[key]
        return int(s.stop - s.start)
    if key in SPECIAL_CHANNEL_DIM:
        return SPECIAL_CHANNEL_DIM[key]
    msg = f"Unknown channel {name!r}"
    raise ValueError(msg)


def channel_dims(channels: Sequence[str] | None) -> list[int]:
    return [channel_dim(c) for c in normalize_channels(channels)]


def measurement_dim(channels: Sequence[str] | None) -> int:
    return int(sum(channel_dims(channels)))


def channel_indices(channels: Sequence[str] | None) -> np.ndarray:
    """
    State indices touched by **linear** packing (for partial_raw init).

    ``body_vel`` maps to NED vel indices (hover-linear / naive bus placement).
    """
    ch = normalize_channels(channels)
    idx: list[int] = []
    for name in ch:
        if name in CHANNEL_SLICES:
            s = CHANNEL_SLICES[name]
            idx.extend(range(s.start, s.stop))
        elif name == "alt":
            idx.append(2)
        elif name == "vel_xy":
            idx.extend([6, 7])
        elif name == "body_vel":
            idx.extend([6, 7, 8])
    return np.asarray(idx, dtype=int)


def measure_channel(x_euler: np.ndarray, name: str) -> np.ndarray:
    """True (noiseless) measurement block for one channel."""
    x = np.asarray(x_euler, dtype=float).reshape(STATE_DIM)
    if name in CHANNEL_SLICES:
        s = CHANNEL_SLICES[name]
        return x[s].copy()
    if name == "alt":
        return np.array([x[2]], dtype=float)
    if name == "vel_xy":
        return x[6:8].copy()
    if name == "body_vel":
        phi, theta, psi = float(x[3]), float(x[4]), float(x[5])
        r_b2i = rotation_body_to_inertial(phi, theta, psi)
        return (r_b2i.T @ x[6:9]).astype(float)
    msg = f"Unknown channel {name!r}"
    raise ValueError(msg)


def pack_measurement(x_euler: np.ndarray, channels: Sequence[str] | None) -> np.ndarray:
    """Extract stacked y from a full Euler state (noiseless)."""
    parts = [measure_channel(x_euler, name) for name in normalize_channels(channels)]
    if not parts:
        return np.zeros(0)
    return np.concatenate(parts)


def selection_matrix(channels: Sequence[str] | None) -> np.ndarray:
    """
    H (m×12) for KF update (hover-linear for ``body_vel``).

    ``body_vel`` uses the NED velocity block — consistent with small-angle
    optical flow where body velocity approximately equals inertial velocity.
    """
    ch = normalize_channels(channels)
    m = measurement_dim(ch)
    h = np.zeros((m, STATE_DIM))
    row = 0
    for name in ch:
        if name in CHANNEL_SLICES:
            s = CHANNEL_SLICES[name]
            for j in range(s.start, s.stop):
                h[row, j] = 1.0
                row += 1
        elif name == "alt":
            h[row, 2] = 1.0
            row += 1
        elif name == "vel_xy":
            h[row, 6] = 1.0
            h[row + 1, 7] = 1.0
            row += 2
        elif name == "body_vel":
            for j in (6, 7, 8):
                h[row, j] = 1.0
                row += 1
    return h


def measurement_noise_diag(
    channels: Sequence[str] | None,
    *,
    pos_sigma_m: float,
    vel_sigma_m_s: float,
    att_sigma_rad: float,
    omega_sigma_rad_s: float,
    alt_sigma_m: float | None = None,
    body_vel_sigma_m_s: float | None = None,
) -> np.ndarray:
    """Diagonal R entries matching stacked channel order."""
    alt_s = pos_sigma_m if alt_sigma_m is None else alt_sigma_m
    bv_s = vel_sigma_m_s if body_vel_sigma_m_s is None else body_vel_sigma_m_s
    sig_block = {
        "pos": max(pos_sigma_m, 1e-9),
        "att": max(att_sigma_rad, 1e-9),
        "vel": max(vel_sigma_m_s, 1e-9),
        "omega": max(omega_sigma_rad_s, 1e-9),
        "alt": max(float(alt_s), 1e-9),
        "vel_xy": max(vel_sigma_m_s, 1e-9),
        "body_vel": max(float(bv_s), 1e-9),
    }
    diags: list[float] = []
    for name in normalize_channels(channels):
        s = sig_block[name]
        diags.extend([s**2] * channel_dim(name))
    return np.asarray(diags, dtype=float)


def validate_channel_list(channels: Iterable[str]) -> list[str]:
    return normalize_channels(list(channels))
