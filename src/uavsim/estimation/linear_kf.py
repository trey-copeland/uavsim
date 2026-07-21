"""Linear Kalman filter on Euler 12-state using hover linearization (Phase 5d)."""

from __future__ import annotations

import numpy as np

from uavsim.dynamics import CONTROL_DIM, STATE_DIM, hover_linearization
from uavsim.vehicles.params import VehicleParams


class LinearStateKalmanFilter:
    """
    Discrete KF: ``x̂⁺ = F x̂ + G u``, ``y = H x + v`` with ``H = I``.

    Process model uses the hover ``(A, B)`` linearized plant (same as LQR design).
    Suitable as a first observer for SIL demos; not a full MEKF.
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
        p0_scale: float = 1.0,
    ) -> None:
        self.vehicle = vehicle
        a, b = hover_linearization(vehicle)
        self._a = np.asarray(a, dtype=float)
        self._b = np.asarray(b, dtype=float)
        self._x = np.zeros(STATE_DIM)
        self._p = np.eye(STATE_DIM) * float(p0_scale)
        # Measurement noise
        r_diag = np.concatenate(
            [
                np.full(3, max(pos_sigma_m, 1e-9) ** 2),
                np.full(3, max(att_sigma_rad, 1e-9) ** 2),
                np.full(3, max(vel_sigma_m_s, 1e-9) ** 2),
                np.full(3, max(omega_sigma_rad_s, 1e-9) ** 2),
            ]
        )
        self._r = np.diag(r_diag)
        # Process noise (state-space white noise intensity * dt applied in predict)
        q_base = max(float(process_sigma), 1e-9) ** 2
        self._q_cont = np.eye(STATE_DIM) * q_base
        self._h = np.eye(STATE_DIM)
        self._t = 0.0

    def reset(self, x0: np.ndarray, t0: float = 0.0) -> None:
        self._x = np.asarray(x0, dtype=float).reshape(STATE_DIM).copy()
        self._p = np.eye(STATE_DIM) * float(np.trace(self._p) / STATE_DIM + 1.0)
        # Keep modest initial covariance
        self._p = np.eye(STATE_DIM) * 0.1
        self._t = float(t0)

    def predict(self, dt: float, u: np.ndarray) -> np.ndarray:
        dt = float(dt)
        if dt <= 0:
            return self._x.copy()
        u = np.asarray(u, dtype=float).reshape(CONTROL_DIM)
        # Discretize about hover: ẋ = A x + B (u - u_hover) + … ; shift control
        u_delta = u - self.vehicle.u_hover()
        f = np.eye(STATE_DIM) + self._a * dt
        g = self._b * dt
        q_d = self._q_cont * dt
        self._x = f @ self._x + g @ u_delta
        self._p = f @ self._p @ f.T + q_d
        # Symmetrize
        self._p = 0.5 * (self._p + self._p.T)
        self._t += dt
        return self._x.copy()

    def update(self, y: np.ndarray) -> np.ndarray:
        y = np.asarray(y, dtype=float).reshape(STATE_DIM)
        h = self._h
        s = h @ self._p @ h.T + self._r
        k = self._p @ h.T @ np.linalg.solve(s, np.eye(STATE_DIM))
        innov = y - h @ self._x
        self._x = self._x + k @ innov
        i_kh = np.eye(STATE_DIM) - k @ h
        self._p = i_kh @ self._p @ i_kh.T + k @ self._r @ k.T
        self._p = 0.5 * (self._p + self._p.T)
        return self._x.copy()

    @property
    def x_hat(self) -> np.ndarray:
        return self._x.copy()
