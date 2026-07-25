"""G-6 adapter rebind + intercept backend registration."""

from __future__ import annotations

import numpy as np

from uavsim.guidance import list_guidance_backends
from uavsim.interfaces import ActuatorCommand
from uavsim.reference import hold_at_ned
from uavsim.sim.adapters import InProcessControllerAdapter


def test_intercept_pursue_registered() -> None:
    assert "intercept_pursue" in list_guidance_backends()


def test_adapter_set_reference() -> None:
    class _C:
        id = "stub"

        def compute(self, t, meas, ref):
            return ActuatorCommand(u=np.array([1.0, 0.0, 0.0, 0.0]))

        @property
        def u_hover(self):
            return np.array([1.0, 0.0, 0.0, 0.0])

    r0 = hold_at_ned(np.zeros(3), duration_s=2.0)
    r1 = hold_at_ned(np.array([1.0, 0.0, 0.0]), duration_s=2.0)
    ad = InProcessControllerAdapter(_C(), r0)
    assert ad.reference is r0
    ad.set_reference(r1)
    assert ad.reference is r1
