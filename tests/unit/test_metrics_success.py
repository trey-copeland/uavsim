"""Tracking success criterion (portfolio-honest 3× bound)."""

from __future__ import annotations

import numpy as np
import pytest

from uavsim.metrics.tracking import compute_metrics
from uavsim.reference import hold_at_ned
from uavsim.vehicles import default_vehicle


def _hold_ref(duration: float = 1.0):
    return hold_at_ned(np.zeros(3), yaw_rad=0.0, duration_s=duration)


def test_success_when_peak_within_3x_bound() -> None:
    t = np.linspace(0, 1, 21)
    x = np.zeros((t.size, 12))
    # Constant 0.2 m north error; bound 0.1 → limit 0.3 → success
    x[:, 0] = 0.2
    u = np.tile(default_vehicle().u_hover(), (t.size, 1))
    m = compute_metrics(t, x, u, _hold_ref(), position_bound_m=0.1)
    assert m["success"] is True
    assert m["success_pos_limit_m"] == pytest.approx(0.3)


def test_fail_when_peak_exceeds_3x_bound() -> None:
    t = np.linspace(0, 1, 21)
    x = np.zeros((t.size, 12))
    x[:, 0] = 0.4  # > 0.3 limit for bound 0.1
    u = np.tile(default_vehicle().u_hover(), (t.size, 1))
    m = compute_metrics(t, x, u, _hold_ref(), position_bound_m=0.1)
    assert m["success"] is False


def test_old_five_x_floor_no_longer_hides_ahrs_scale_error() -> None:
    """Former rule max(5*bound, 1) let max|e|=4.3 m pass with bound=1."""
    t = np.linspace(0, 1, 11)
    x = np.zeros((t.size, 12))
    x[:, 0] = 4.3
    u = np.tile(default_vehicle().u_hover(), (t.size, 1))
    m = compute_metrics(t, x, u, _hold_ref(), position_bound_m=1.0)
    assert m["success_pos_limit_m"] == pytest.approx(3.0)
    assert m["success"] is False
