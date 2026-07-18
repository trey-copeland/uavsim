"""Waypoints guidance backend: mission file → interp / minsnap / auto."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from uavsim.guidance.base import PlanResult, register_guidance
from uavsim.guidance.waypoints.auto import select_waypoint_method
from uavsim.guidance.waypoints.interp import generate_interp_trajectory
from uavsim.guidance.waypoints.minsnap import generate_minsnap_trajectory
from uavsim.guidance.waypoints.mission import WaypointMission, load_mission
from uavsim.guidance.waypoints.yaw import YawMode
from uavsim.reference import FeasibilityLimits, check_sampled_feasibility
from uavsim.vehicles.params import VehicleParams

MethodName = Literal["auto", "interp", "minsnap"]


class WaypointsGuidance:
    """Backend id ``waypoints``."""

    id = "waypoints"

    def __init__(
        self,
        *,
        method: MethodName = "auto",
        yaw_mode: YawMode = "constant",
        sample_dt_s: float = 0.01,
        fail_on_infeasible: bool = False,
        feasibility_limits: FeasibilityLimits | None = None,
    ) -> None:
        self.method = method
        self.yaw_mode = yaw_mode
        self.sample_dt_s = sample_dt_s
        self.fail_on_infeasible = fail_on_infeasible
        self.feasibility_limits = feasibility_limits or FeasibilityLimits()

    def plan(
        self,
        mission: dict[str, Any],
        vehicle: VehicleParams,
        *,
        rng: Any | None = None,
    ) -> PlanResult:
        _ = rng
        mission_obj = self._resolve_mission(mission)
        method = self.method
        auto_diag: dict[str, Any] = {}
        if method == "auto":
            method, auto_diag = select_waypoint_method(mission_obj)

        if method == "interp":
            reference = generate_interp_trajectory(
                mission_obj,
                dt_s=self.sample_dt_s,
                yaw_mode=self.yaw_mode,
                g=vehicle.gravity_m_s2,
            )
            costs: dict[str, float] = {}
        elif method == "minsnap":
            reference, costs = generate_minsnap_trajectory(
                mission_obj,
                dt_s=self.sample_dt_s,
                yaw_mode=self.yaw_mode,
                g=vehicle.gravity_m_s2,
            )
        else:
            msg = f"Unknown waypoint method after resolve: {method!r}"
            raise ValueError(msg)

        feasibility = check_sampled_feasibility(reference, vehicle, self.feasibility_limits)
        if self.fail_on_infeasible and not feasibility.ok:
            codes = [i.code for i in feasibility.issues if i.severity == "fail"]
            msg = f"Trajectory infeasible (fail issues: {codes})"
            raise RuntimeError(msg)

        diagnostics: dict[str, Any] = {
            "requested_method": self.method,
            "resolved_method": method,
            "yaw_mode": self.yaw_mode,
            "mission_name": mission_obj.name,
            "n_waypoints": len(mission_obj.waypoints),
            "snap_cost": costs,
            **auto_diag,
        }
        return PlanResult(
            reference=reference,
            feasibility=feasibility,
            diagnostics=diagnostics,
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

    @staticmethod
    def _resolve_mission(mission: dict[str, Any]) -> WaypointMission:
        if "mission" in mission and isinstance(mission["mission"], WaypointMission):
            return mission["mission"]
        if "mission_file" in mission:
            return load_mission(Path(mission["mission_file"]))
        if "waypoints" in mission:
            # Inline mission dict
            from uavsim.guidance.waypoints.mission import _normalize_raw

            return WaypointMission.model_validate(_normalize_raw(mission))
        msg = "Waypoints mission must provide mission_file, inline waypoints, or mission object"
        raise ValueError(msg)


register_guidance("waypoints", WaypointsGuidance)
