"""Rotation helpers (ZYX Euler, NED/body)."""

from __future__ import annotations

import numpy as np


def rotation_body_to_inertial(phi: float, theta: float, psi: float) -> np.ndarray:
    """R_b2i = Rz(psi) @ Ry(theta) @ Rx(phi). Maps body vectors to NED inertial."""
    c_phi, s_phi = np.cos(phi), np.sin(phi)
    c_th, s_th = np.cos(theta), np.sin(theta)
    c_psi, s_psi = np.cos(psi), np.sin(psi)

    rx = np.array([[1.0, 0.0, 0.0], [0.0, c_phi, -s_phi], [0.0, s_phi, c_phi]])
    ry = np.array([[c_th, 0.0, s_th], [0.0, 1.0, 0.0], [-s_th, 0.0, c_th]])
    rz = np.array([[c_psi, -s_psi, 0.0], [s_psi, c_psi, 0.0], [0.0, 0.0, 1.0]])
    return rz @ ry @ rx


def euler_rate_matrix(phi: float, theta: float) -> np.ndarray:
    """Map body rates ω=[p,q,r] to Euler rates [φ̇, θ̇, ψ̇] (ZYX)."""
    c_phi, s_phi = np.cos(phi), np.sin(phi)
    c_th = np.cos(theta)
    if abs(c_th) < 1e-6:
        c_th = 1e-6 * np.sign(c_th) if c_th != 0 else 1e-6
    t_th = np.tan(theta)
    return np.array(
        [
            [1.0, s_phi * t_th, c_phi * t_th],
            [0.0, c_phi, -s_phi],
            [0.0, s_phi / c_th, c_phi / c_th],
        ]
    )
