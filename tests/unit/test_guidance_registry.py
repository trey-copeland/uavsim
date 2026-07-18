"""Guidance registry + non-waypoint stub backend (architecture acceptance)."""

from __future__ import annotations

from typing import Any

import numpy as np

from uavsim.control import design_lqr_hover
from uavsim.guidance.base import (
    PlanResult,
    create_guidance,
    list_guidance_backends,
    register_guidance,
)
from uavsim.reference import FeasibilityReport, HoldReference, hold_at_ned
from uavsim.sim import InProcessControllerAdapter, SimPlant, simulate_closed_loop
from uavsim.vehicles.params import default_vehicle


class GeometricStubGuidance:
    """Non-waypoint backend: circular-ish hold offset (proves registry seam)."""

    id = "geometric_stub"

    def plan(
        self,
        mission: dict[str, Any],
        vehicle: Any,
        *,
        rng: Any | None = None,
    ) -> PlanResult:
        _ = (vehicle, rng)
        radius = float(mission.get("radius_m", 0.0))
        # Constant hover offset — not a real geometric planner
        pos = np.array([radius, 0.0, 1.0])
        ref = hold_at_ned(pos, duration_s=float(mission.get("duration_s", 2.0)))
        ref.backend_id = self.id
        return PlanResult(
            reference=ref,
            feasibility=FeasibilityReport(ok=True, issues=[], summary={}),
            diagnostics={"stub": True},
        )

    def update(
        self,
        state: Any,
        t: float,
        mission: dict[str, Any],
        vehicle: Any,
        reference: Any,
        *,
        rng: Any | None = None,
    ) -> PlanResult | None:
        _ = (state, t, mission, vehicle, reference, rng)
        return None


def test_core_backends_registered() -> None:
    # Import package side effects
    import uavsim.guidance  # noqa: F401

    known = list_guidance_backends()
    assert "hold" in known
    assert "waypoints" in known


def test_stub_backend_drives_closed_loop() -> None:
    register_guidance("geometric_stub", GeometricStubGuidance)
    backend = create_guidance("geometric_stub")
    vehicle = default_vehicle()
    plan = backend.plan({"radius_m": 0.0, "duration_s": 2.0}, vehicle)
    assert plan.reference.backend_id == "geometric_stub"
    assert isinstance(plan.reference, HoldReference)

    controller = design_lqr_hover(vehicle)
    plant = SimPlant(vehicle)
    adapter = InProcessControllerAdapter(controller, plan.reference)
    x0 = plan.reference.evaluate(0.0).x_ref.copy()
    result = simulate_closed_loop(
        plant,
        adapter,
        t0=plan.reference.t0,
        tf=plan.reference.tf,
        x0=x0,
        max_step=0.02,
    )
    assert result.success
    assert np.isfinite(result.x).all()
