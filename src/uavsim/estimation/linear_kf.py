"""Linear Kalman filter on Euler 12-state using hover linearization (Phase 5d)."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from uavsim.dynamics import CONTROL_DIM, STATE_DIM, hover_linearization
from uavsim.estimation.channels import (
    measurement_noise_diag,
    normalize_channels,
    selection_matrix,
)
from uavsim.estimation.measurements import Observation
from uavsim.vehicles.params import VehicleParams


class LinearStateKalmanFilter:
    """
    Discrete KF: ``x̂⁺ = F x̂ + G u_δ``, ``y = H x + v``.

    ``H`` is full identity by default, or a channel selection matrix for
    partial-state measurements (e.g. pos + gyro only).
    """

    id = "linear_kf"

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
        a, b = hover_linearization(vehicle)
        self._a = np.asarray(a, dtype=float)
        self._b = np.asarray(b, dtype=float)
        self._x = np.zeros(STATE_DIM)
        self._p = np.eye(STATE_DIM) * 0.1
        self.channels = normalize_channels(channels)
        self._h_default = selection_matrix(self.channels)
        r_diag = measurement_noise_diag(
            self.channels,
            pos_sigma_m=pos_sigma_m,
            vel_sigma_m_s=vel_sigma_m_s,
            att_sigma_rad=att_sigma_rad,
            omega_sigma_rad_s=omega_sigma_rad_s,
        )
        self._r_default = np.diag(r_diag)
        q_base = max(float(process_sigma), 1e-9) ** 2
        self._q_cont = np.eye(STATE_DIM) * q_base
        self._t = 0.0

    def reset(self, x0: np.ndarray, t0: float = 0.0) -> None:
        self._x = np.asarray(x0, dtype=float).reshape(STATE_DIM).copy()
        self._p = np.eye(STATE_DIM) * 0.1
        self._t = float(t0)

    def predict(self, dt: float, u: np.ndarray) -> np.ndarray:
        dt = float(dt)
        if dt <= 0:
            return self._x.copy()
        u = np.asarray(u, dtype=float).reshape(CONTROL_DIM)
        u_delta = u - self.vehicle.u_hover()
        f = np.eye(STATE_DIM) + self._a * dt
        g = self._b * dt
        q_d = self._q_cont * dt
        self._x = f @ self._x + g @ u_delta
        self._p = f @ self._p @ f.T + q_d
        self._p = 0.5 * (self._p + self._p.T)
        self._t += dt
        return self._x.copy()

    def update(self, y: np.ndarray | Observation) -> np.ndarray:
        if isinstance(y, Observation):
            y_vec = np.asarray(y.y, dtype=float).reshape(-1)
            h = np.asarray(y.h, dtype=float)
            r = np.asarray(y.r, dtype=float)
        else:
            y_arr = np.asarray(y, dtype=float).reshape(-1)
            if y_arr.size == STATE_DIM:
                # Full-state vector: select configured channels
                h = self._h_default
                y_vec = h @ y_arr
                r = self._r_default
            else:
                h = self._h_default
                y_vec = y_arr
                r = self._r_default
                if y_vec.size != h.shape[0]:
                    msg = f"y length {y_vec.size} != H rows {h.shape[0]}"
                    raise ValueError(msg)

        s = h @ self._p @ h.T + r
        k = self._p @ h.T @ np.linalg.solve(s, np.eye(h.shape[0]))
        innov = y_vec - h @ self._x
        self._x = self._x + k @ innov
        i_kh = np.eye(STATE_DIM) - k @ h
        self._p = i_kh @ self._p @ i_kh.T + k @ r @ k.T
        self._p = 0.5 * (self._p + self._p.T)
        return self._x.copy()

    @property
    def x_hat(self) -> np.ndarray:
        return self._x.copy()
