"""Rotation helpers (ZYX Euler + unit quaternions, NED/body).

Quaternion convention (scalar-first):
  ``q = [qw, qx, qy, qz]`` unit, maps **body → inertial (NED)** via
  ``v_i = R_b2i(q) @ v_b``.
"""

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


def quat_normalize(q: np.ndarray) -> np.ndarray:
    """Return unit quaternion; empty / zero → identity."""
    q = np.asarray(q, dtype=float).reshape(4)
    n = float(np.linalg.norm(q))
    if n < 1e-15:
        return np.array([1.0, 0.0, 0.0, 0.0])
    return q / n


def quat_multiply(q1: np.ndarray, q2: np.ndarray) -> np.ndarray:
    """Hamilton product q1 ⊗ q2 (scalar-first)."""
    w1, x1, y1, z1 = np.asarray(q1, dtype=float).reshape(4)
    w2, x2, y2, z2 = np.asarray(q2, dtype=float).reshape(4)
    return np.array(
        [
            w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
            w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
            w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
            w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
        ]
    )


def quat_conjugate(q: np.ndarray) -> np.ndarray:
    q = np.asarray(q, dtype=float).reshape(4)
    return np.array([q[0], -q[1], -q[2], -q[3]])


def rotation_body_to_inertial_quat(q: np.ndarray) -> np.ndarray:
    """Direction cosine matrix body → inertial from unit quaternion."""
    q = quat_normalize(q)
    w, x, y, z = q
    return np.array(
        [
            [
                1.0 - 2.0 * (y * y + z * z),
                2.0 * (x * y - z * w),
                2.0 * (x * z + y * w),
            ],
            [
                2.0 * (x * y + z * w),
                1.0 - 2.0 * (x * x + z * z),
                2.0 * (y * z - x * w),
            ],
            [
                2.0 * (x * z - y * w),
                2.0 * (y * z + x * w),
                1.0 - 2.0 * (x * x + y * y),
            ],
        ]
    )


def euler_to_quat(phi: float, theta: float, psi: float) -> np.ndarray:
    """ZYX Euler (rad) → unit quaternion (body→inertial)."""
    # Half-angles
    cr, sr = np.cos(phi * 0.5), np.sin(phi * 0.5)
    cp, sp = np.cos(theta * 0.5), np.sin(theta * 0.5)
    cy, sy = np.cos(psi * 0.5), np.sin(psi * 0.5)
    # ZYX: q = qz ⊗ qy ⊗ qx
    qw = cr * cp * cy + sr * sp * sy
    qx = sr * cp * cy - cr * sp * sy
    qy = cr * sp * cy + sr * cp * sy
    qz = cr * cp * sy - sr * sp * cy
    return quat_normalize(np.array([qw, qx, qy, qz]))


def quat_to_euler(q: np.ndarray) -> np.ndarray:
    """Unit quaternion → ZYX Euler [φ, θ, ψ] (rad). Pitch clamped near ±π/2."""
    q = quat_normalize(q)
    w, x, y, z = q
    # roll (x-axis)
    sinr_cosp = 2.0 * (w * x + y * z)
    cosr_cosp = 1.0 - 2.0 * (x * x + y * y)
    phi = float(np.arctan2(sinr_cosp, cosr_cosp))
    # pitch (y-axis)
    sinp = 2.0 * (w * y - z * x)
    sinp = float(np.clip(sinp, -1.0, 1.0))
    theta = float(np.arcsin(sinp))
    # yaw (z-axis)
    siny_cosp = 2.0 * (w * z + x * y)
    cosy_cosp = 1.0 - 2.0 * (y * y + z * z)
    psi = float(np.arctan2(siny_cosp, cosy_cosp))
    return np.array([phi, theta, psi])


def quat_derivative_body_rates(q: np.ndarray, omega: np.ndarray) -> np.ndarray:
    """
    Quaternion kinematics for body rates ω=[p,q,r]:

      q̇ = ½ q ⊗ [0, ω]
    """
    q = quat_normalize(q)
    omega = np.asarray(omega, dtype=float).reshape(3)
    omega_q = np.array([0.0, omega[0], omega[1], omega[2]])
    return 0.5 * quat_multiply(q, omega_q)
