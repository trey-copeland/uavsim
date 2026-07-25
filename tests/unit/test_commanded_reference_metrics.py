"""Tracking metrics must use per-tick commanded x_r under online replan."""

from __future__ import annotations

import numpy as np
import pytest

from uavsim.interfaces import ActuatorCommand, MeasurementBus
from uavsim.metrics.tracking import compute_metrics
from uavsim.reference import SampledReference, hold_at_ned
from uavsim.sim.adapters import InProcessControllerAdapter
from uavsim.vehicles import default_vehicle


def test_adapter_records_last_sample() -> None:
    class _C:
        id = "stub"

        def compute(self, t, meas, ref):
            return ActuatorCommand(u=np.array([1.0, 0.0, 0.0, 0.0]))

        @property
        def u_hover(self):
            return np.array([1.0, 0.0, 0.0, 0.0])

    ref = hold_at_ned(np.array([1.0, 2.0, 3.0]), duration_s=2.0)
    ad = InProcessControllerAdapter(_C(), ref)
    assert ad.last_sample is None
    ad.command(0.5, MeasurementBus(t=0.5, x=np.zeros(12)))
    assert ad.last_sample is not None
    np.testing.assert_allclose(ad.last_sample.x_ref[0:3], [1.0, 2.0, 3.0])


def test_compute_metrics_prefers_commanded_x_ref_over_final_segment() -> None:
    """Synthetic online-replan trap: final segment only covers late times."""
    t = np.linspace(0.0, 10.0, 101)
    # Plant tracks a climb then fly-north path (truth)
    x = np.zeros((t.size, 12))
    x[:, 0] = np.clip(t - 2.0, 0.0, None) * 2.0  # N
    x[:, 2] = 3.0 - np.minimum(t, 2.0) * 0.5  # z (NED down-ish toy)
    # Commanded reference = same as truth (perfect tracking)
    x_cmd = x.copy()
    # Final replan segment only: t in [9.8, 10], start at end of path
    t_seg = np.array([9.8, 10.0])
    x_seg = np.vstack([x[-1], x[-1]])
    final_only = SampledReference(
        t0=9.8,
        tf=10.0,
        t_grid=t_seg,
        x_grid=x_seg,
        backend_id="toy_final_segment",
    )
    u = np.tile(default_vehicle().u_hover(), (t.size, 1))

    bad = compute_metrics(t, x, u, final_only, position_bound_m=1.0)
    good = compute_metrics(t, x, u, final_only, position_bound_m=1.0, x_ref=x_cmd)

    # Re-evaluating final segment clamps early t → huge fake error
    assert bad["rmse_position_m"] > 5.0
    assert bad["tracking_vs_commanded_reference"] is False
    # Commanded samples → near-zero RMSE
    assert good["rmse_position_m"] == pytest.approx(0.0, abs=1e-12)
    assert good["tracking_vs_commanded_reference"] is True
    assert good["success"] is True
