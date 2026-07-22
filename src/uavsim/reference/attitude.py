"""Feedforward attitude helpers for reference trajectories (NED / FRD)."""

from __future__ import annotations

import numpy as np


def feedforward_roll_pitch(
    accel_ned: np.ndarray,
    g: float = 9.81,
    *,
    max_tilt_rad: float = np.deg2rad(35.0),
) -> tuple[np.ndarray, np.ndarray]:
    """
    Approximate roll/pitch for a desired inertial acceleration at constant yaw=0.

    Must match the plant (NED, thrust along −body-z). At hover thrust:

      ẍ ≈ −g sin θ  ⇒  θ ≈ −asin(a_x / g)
      ÿ ≈ +g sin φ  ⇒  φ ≈ +asin(a_y / (g cos θ))

    (Same signs as ``hover_linearization`` and the PID outer loop.)

    Returns (roll, pitch) arrays matching the first axis of ``accel_ned``.
    """
    a = np.asarray(accel_ned, dtype=float)
    if a.ndim == 1:
        a = a.reshape(1, 3)
    ax = a[:, 0]
    ay = a[:, 1]

    # Clip horizontal accel to max tilt equivalent
    a_max = g * np.sin(max_tilt_rad)
    horiz = np.hypot(ax, ay)
    scale = np.ones_like(horiz)
    over = horiz > a_max
    scale[over] = a_max / horiz[over]
    ax = ax * scale
    ay = ay * scale

    # Plant: a_x = -g sin θ  →  sin θ = -a_x / g
    sin_theta = np.clip(-ax / g, -1.0, 1.0)
    theta = np.arcsin(sin_theta)
    cos_theta = np.cos(theta)
    # Avoid divide-by-zero at extreme pitch; plant: a_y = g sin φ (level yaw)
    denom = np.maximum(g * np.maximum(np.abs(cos_theta), 1e-6), 1e-6)
    sin_phi = np.clip(ay / denom, -1.0, 1.0)
    phi = np.arcsin(sin_phi)
    return phi, theta


def body_rates_from_euler(
    t: np.ndarray,
    euler: np.ndarray,
) -> np.ndarray:
    """
    Approximate body rates p,q,r from Euler angle time series (ZYX).

    Uses central differences for Euler rates then the standard kinematic map.
    """
    t = np.asarray(t, dtype=float).reshape(-1)
    euler = np.asarray(euler, dtype=float)
    n = t.size
    if n < 2:
        return np.zeros((n, 3), dtype=float)

    de = np.gradient(euler, t, axis=0)
    phi = euler[:, 0]
    theta = euler[:, 1]
    # ė = W(φ,θ) ω  ⇒  ω = W^{-1} ė
    # W = [[1, sφ tθ, cφ tθ], [0, cφ, -sφ], [0, sφ/cθ, cφ/cθ]]
    # inverse is well-known for aerospace ZYX:
    omega = np.zeros((n, 3), dtype=float)
    for i in range(n):
        cth = np.cos(theta[i])
        sth = np.sin(theta[i])
        cph = np.cos(phi[i])
        sph = np.sin(phi[i])
        # Guard near pitch singularity
        if abs(cth) < 1e-6:
            omega[i] = 0.0
            continue
        # ė = [φ̇, θ̇, ψ̇]
        edot = de[i]
        # ω = [
        #   φ̇ - ψ̇ sin θ
        #   θ̇ cos φ + ψ̇ sin φ cos θ
        #  -θ̇ sin φ + ψ̇ cos φ cos θ
        # ]
        omega[i, 0] = edot[0] - edot[2] * sth
        omega[i, 1] = edot[1] * cph + edot[2] * sph * cth
        omega[i, 2] = -edot[1] * sph + edot[2] * cph * cth
    return omega
