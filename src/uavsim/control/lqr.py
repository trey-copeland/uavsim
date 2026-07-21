"""LQR hover controller design and evaluation."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.linalg import solve_continuous_are

from uavsim.control.base import saturate
from uavsim.dynamics import CONTROL_DIM, STATE_DIM, hover_linearization
from uavsim.dynamics.attitude_error import tracking_error_state
from uavsim.interfaces import ActuatorCommand, MeasurementBus
from uavsim.reference import ReferenceSample
from uavsim.vehicles.params import VehicleParams

# Heritage-inspired defaults
DEFAULT_Q_DIAG = np.array([100, 100, 100, 10, 10, 1, 10, 10, 10, 1, 1, 0.1], dtype=float)
DEFAULT_R_DIAG = np.array([0.1, 1.0, 1.0, 1.0], dtype=float)


@dataclass
class LqrHoverController:
    """u = u_hover - K e, with e an error-state (SO(3) attitude), actuator saturation."""

    id: str
    vehicle: VehicleParams
    k: np.ndarray
    q: np.ndarray
    r: np.ndarray
    poles: np.ndarray

    @property
    def u_hover(self) -> np.ndarray:
        return self.vehicle.u_hover()

    def compute(
        self,
        t: float,
        measurements: MeasurementBus,
        reference: ReferenceSample,
    ) -> ActuatorCommand:
        _ = t
        # Error-state: δθ from R_ref^T R (matches linearization near hover)
        e = tracking_error_state(measurements.x, reference.x_ref)
        u = self.u_hover - self.k @ e
        u = saturate(u, self.vehicle.limits.u_min(), self.vehicle.limits.u_max())
        return ActuatorCommand(u=u)


def design_lqr_hover(
    vehicle: VehicleParams,
    q_diag: np.ndarray | None = None,
    r_diag: np.ndarray | None = None,
    controller_id: str = "lqr_hover",
) -> LqrHoverController:
    q_diag = DEFAULT_Q_DIAG if q_diag is None else np.asarray(q_diag, dtype=float)
    r_diag = DEFAULT_R_DIAG if r_diag is None else np.asarray(r_diag, dtype=float)
    if q_diag.shape != (STATE_DIM,):
        msg = f"Q_diag must have length {STATE_DIM}"
        raise ValueError(msg)
    if r_diag.shape != (CONTROL_DIM,):
        msg = f"R_diag must have length {CONTROL_DIM}"
        raise ValueError(msg)

    q = np.diag(q_diag)
    r = np.diag(r_diag)
    a, b = hover_linearization(vehicle)
    # Continuous ARE: A'P + PA - PBR^{-1}B'P + Q = 0
    p = solve_continuous_are(a, b, q, r)
    k = np.linalg.solve(r, b.T @ p)

    a_cl = a - b @ k
    poles = np.linalg.eigvals(a_cl)
    if np.any(np.real(poles) >= 0):
        msg = "LQR closed-loop has non-negative real-part eigenvalues"
        raise RuntimeError(msg)

    return LqrHoverController(
        id=controller_id,
        vehicle=vehicle,
        k=k,
        q=q,
        r=r,
        poles=poles,
    )
