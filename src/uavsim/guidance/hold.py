"""Hold (constant setpoint) guidance backend."""

from __future__ import annotations

from typing import Any

import numpy as np

from uavsim.guidance.base import PlanResult, register_guidance
from uavsim.reference import check_reference_feasibility, hold_at_ned
from uavsim.vehicles.params import VehicleParams


class HoldGuidance:
    """Backend id ``hold``: constant NED position + yaw over a duration."""

    id = "hold"

    def plan(
        self,
        mission: dict[str, Any],
        vehicle: VehicleParams,
        *,
        rng: Any | None = None,
    ) -> PlanResult:
        _ = rng
        pos = np.asarray(mission["position_ned_m"], dtype=float)
        yaw = float(mission.get("yaw_rad", 0.0))
        duration = float(mission.get("duration_s", 5.0))
        reference = hold_at_ned(pos, yaw_rad=yaw, duration_s=duration)
        feasibility = check_reference_feasibility(reference, vehicle)
        return PlanResult(
            reference=reference,
            feasibility=feasibility,
            diagnostics={"method": "hold"},
        )

    def update(
        self,
        state: Any,
        t: float,
        mission: dict[str, Any],
        vehicle: VehicleParams,
        reference: Any,
        *,
        rng: Any | None = None,
    ) -> PlanResult | None:
        _ = (state, t, mission, vehicle, reference, rng)
        return None


register_guidance("hold", HoldGuidance)
