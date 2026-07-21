"""Error-state (multiplicative) attitude EKF + translation (Phase 5d stretch)."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from uavsim.dynamics import CONTROL_DIM, STATE_DIM
from uavsim.dynamics.rotations import (
    euler_to_quat,
    quat_conjugate,
    quat_multiply,
    quat_normalize,
    quat_to_euler,
    rotation_body_to_inertial_quat,
)
from uavsim.estimation.channels import (
    measurement_noise_diag,
    normalize_channels,
    pack_measurement,
    selection_matrix,
)
from uavsim.estimation.measurements import Observation
from uavsim.vehicles.params import VehicleParams

ERR_DIM = 9  # δp, δv, δθ


def _skew(v: np.ndarray) -> np.ndarray:
    x, y, z = float(v[0]), float(v[1]), float(v[2])
    return np.array([[0.0, -z, y], [z, 0.0, -x], [-y, x, 0.0]])


def _quat_from_rotvec(dth: np.ndarray) -> np.ndarray:
    dth = np.asarray(dth, dtype=float).reshape(3)
    angle = float(np.linalg.norm(dth))
    if angle < 1e-12:
        return quat_normalize(np.array([1.0, 0.5 * dth[0], 0.5 * dth[1], 0.5 * dth[2]]))
    axis = dth / angle
    s = np.sin(0.5 * angle)
    return quat_normalize(np.array([np.cos(0.5 * angle), *(axis * s)]))


class ErrorStateMekf:
    """
    MEKF-class filter: nominal (p, v, q, ω) + error [δp, δv, δθ].

    Multiplicative attitude updates; supports partial channels via Observation.
    """

    id = "mekf"

    def __init__(
        self,
        vehicle: VehicleParams,
        *,
        pos_sigma_m: float = 0.05,
        vel_sigma_m_s: float = 0.05,
        att_sigma_rad: float = 0.02,
        omega_sigma_rad_s: float = 0.05,
        process_sigma: float = 0.02,
        channels: Sequence[str] | None = None,
    ) -> None:
        self.vehicle = vehicle
        self.channels = normalize_channels(channels)
        self._p = np.zeros(3)
        self._v = np.zeros(3)
        self._q = np.array([1.0, 0.0, 0.0, 0.0])
        self._omega = np.zeros(3)
        self._p_cov = np.eye(ERR_DIM) * 0.1
        self._sig = {
            "pos": max(pos_sigma_m, 1e-9),
            "vel": max(vel_sigma_m_s, 1e-9),
            "att": max(att_sigma_rad, 1e-9),
            "omega": max(omega_sigma_rad_s, 1e-9),
        }
        q0 = max(float(process_sigma), 1e-9) ** 2
        self._q_cont = np.diag([q0] * 6 + [0.5 * q0] * 3)
        self._t = 0.0

    def reset(self, x0: np.ndarray, t0: float = 0.0) -> None:
        x0 = np.asarray(x0, dtype=float).reshape(STATE_DIM)
        self._p = x0[0:3].copy()
        self._v = x0[6:9].copy()
        self._q = euler_to_quat(float(x0[3]), float(x0[4]), float(x0[5]))
        self._omega = x0[9:12].copy()
        self._p_cov = np.eye(ERR_DIM) * 0.1
        self._t = float(t0)

    def _x_euler(self) -> np.ndarray:
        eul = quat_to_euler(self._q)
        x = np.zeros(STATE_DIM)
        x[0:3] = self._p
        x[3:6] = eul
        x[6:9] = self._v
        x[9:12] = self._omega
        return x

    @property
    def x_hat(self) -> np.ndarray:
        return self._x_euler()

    def predict(self, dt: float, u: np.ndarray) -> np.ndarray:
        dt = float(dt)
        if dt <= 0:
            return self.x_hat
        u = np.asarray(u, dtype=float).reshape(CONTROL_DIM)
        m = self.vehicle.mass_kg
        g = self.vehicle.gravity_m_s2
        inertia = self.vehicle.inertia.as_diag()
        f_thrust = float(u[0])
        tau = u[1:4]

        r_b2i = rotation_body_to_inertial_quat(self._q)
        a_i = (r_b2i @ np.array([0.0, 0.0, -f_thrust]) + np.array([0.0, 0.0, m * g])) / m
        self._p = self._p + self._v * dt + 0.5 * a_i * dt * dt
        self._v = self._v + a_i * dt
        omega_dot = np.linalg.solve(inertia, tau - np.cross(self._omega, inertia @ self._omega))
        self._omega = self._omega + omega_dot * dt
        omega_q = np.array([0.0, self._omega[0], self._omega[1], self._omega[2]])
        self._q = quat_normalize(self._q + 0.5 * quat_multiply(self._q, omega_q) * dt)

        f = np.eye(ERR_DIM)
        f[0:3, 3:6] = np.eye(3) * dt
        f[6:9, 6:9] = np.eye(3) - _skew(self._omega) * dt
        self._p_cov = f @ self._p_cov @ f.T + self._q_cont * dt
        self._p_cov = 0.5 * (self._p_cov + self._p_cov.T)
        self._t += dt
        return self.x_hat

    def update(self, y: np.ndarray | Observation) -> np.ndarray:
        if isinstance(y, Observation):
            obs = y
        else:
            y_arr = np.asarray(y, dtype=float).reshape(-1)
            if y_arr.size != STATE_DIM:
                msg = f"MEKF expects Observation or 12-state, got len={y_arr.size}"
                raise ValueError(msg)
            h = selection_matrix(self.channels)
            y_vec = pack_measurement(y_arr, self.channels)
            r = np.diag(
                measurement_noise_diag(
                    self.channels,
                    pos_sigma_m=self._sig["pos"],
                    vel_sigma_m_s=self._sig["vel"],
                    att_sigma_rad=self._sig["att"],
                    omega_sigma_rad_s=self._sig["omega"],
                )
            )
            obs = Observation(y=y_vec, h=h, r=r, channels=list(self.channels))
        return self._update_observation(obs)

    def _update_observation(self, obs: Observation) -> np.ndarray:
        h12 = np.asarray(obs.h, dtype=float)
        y = np.asarray(obs.y, dtype=float).reshape(-1)
        r = np.asarray(obs.r, dtype=float)
        m_rows = h12.shape[0]
        h_e = np.zeros((m_rows, ERR_DIM))
        h_e[:, 0:3] = h12[:, 0:3]
        h_e[:, 3:6] = h12[:, 6:9]
        h_e[:, 6:9] = h12[:, 3:6]

        x_nom = self._x_euler()
        y_pred = h12 @ x_nom
        innov = y - y_pred

        # Multiplicative attitude residual for att block in channel order
        offset = 0
        for ch in obs.channels:
            if ch == "att":
                eul_meas = y[offset : offset + 3]
                q_meas = euler_to_quat(float(eul_meas[0]), float(eul_meas[1]), float(eul_meas[2]))
                q_err = quat_multiply(quat_conjugate(self._q), q_meas)
                if q_err[0] < 0.0:
                    q_err = -q_err
                dth = 2.0 * q_err[1:4]
                innov[offset : offset + 3] = dth
            if ch == "omega":
                # Direct rate blend handled after KF step
                pass
            offset += 3

        if np.linalg.norm(h_e) > 1e-15:
            s = h_e @ self._p_cov @ h_e.T + r + np.eye(m_rows) * 1e-12
            k = self._p_cov @ h_e.T @ np.linalg.solve(s, np.eye(m_rows))
            dx = k @ innov
            self._p = self._p + dx[0:3]
            self._v = self._v + dx[3:6]
            self._q = quat_normalize(quat_multiply(self._q, _quat_from_rotvec(dx[6:9])))
            i_kh = np.eye(ERR_DIM) - k @ h_e
            self._p_cov = i_kh @ self._p_cov @ i_kh.T + k @ r @ k.T
            self._p_cov = 0.5 * (self._p_cov + self._p_cov.T)

        if "omega" in obs.channels:
            offset = 0
            for ch in obs.channels:
                if ch == "omega":
                    y_w = y[offset : offset + 3]
                    self._omega = 0.5 * self._omega + 0.5 * y_w
                offset += 3
        return self.x_hat
