"""Hover linearization for LQR design (heritage A/B structure)."""

from __future__ import annotations

import numpy as np

from uavsim.dynamics.nonlinear import CONTROL_DIM, STATE_DIM
from uavsim.vehicles.params import VehicleParams


def hover_linearization(vehicle: VehicleParams) -> tuple[np.ndarray, np.ndarray]:
    """
    Linearize about hover: x≈0, u=[mg,0,0,0], small-angle.

    ẍ ≈ -g θ,  ÿ ≈ +g φ  (NED, thrust along −body-z).
    """
    a = np.zeros((STATE_DIM, STATE_DIM))
    b = np.zeros((STATE_DIM, CONTROL_DIM))

    # Position rates = velocity
    a[0, 6] = 1.0
    a[1, 7] = 1.0
    a[2, 8] = 1.0
    # Euler rates ≈ body rates (small angle)
    a[3, 9] = 1.0
    a[4, 10] = 1.0
    a[5, 11] = 1.0
    # Translational accel from tilt
    a[6, 4] = -vehicle.gravity_m_s2  # ẍ ← θ
    a[7, 3] = vehicle.gravity_m_s2  # ÿ ← φ

    b[8, 0] = -1.0 / vehicle.mass_kg  # ż ← F (NED +z down)
    b[9, 1] = 1.0 / vehicle.inertia.ixx_kg_m2
    b[10, 2] = 1.0 / vehicle.inertia.iyy_kg_m2
    b[11, 3] = 1.0 / vehicle.inertia.izz_kg_m2
    return a, b
