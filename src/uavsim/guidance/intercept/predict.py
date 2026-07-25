"""Pure helpers for intercept lead-point prediction (no sim imports)."""

from __future__ import annotations

import numpy as np


def predict_constant_velocity(
    position: np.ndarray,
    velocity: np.ndarray,
    lead_time_s: float,
) -> np.ndarray:
    """``p* = p + v * t_lead``."""
    p = np.asarray(position, dtype=float).reshape(3)
    v = np.asarray(velocity, dtype=float).reshape(3)
    return p + v * float(lead_time_s)


def closing_speed(own_vel: np.ndarray, tgt_vel: np.ndarray, los: np.ndarray) -> float:
    """Component of relative velocity along line-of-sight (positive = closing)."""
    rel = np.asarray(tgt_vel, dtype=float).reshape(3) - np.asarray(own_vel, dtype=float).reshape(3)
    r = np.asarray(los, dtype=float).reshape(3)
    n = float(np.linalg.norm(r))
    if n < 1e-12:
        return 0.0
    return float(-np.dot(rel, r / n))
