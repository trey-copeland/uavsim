"""Online intercept pursuit: scripted target + short-horizon ownship replan."""

from __future__ import annotations

from typing import Any, Literal

import numpy as np

from uavsim.dynamics import STATE_DIM
from uavsim.guidance.base import PlanResult, register_guidance
from uavsim.guidance.intercept.predict import predict_constant_velocity
from uavsim.guidance.waypoints.backend import WaypointsGuidance
from uavsim.reference import SampledReference, check_reference_feasibility
from uavsim.reference.types import ReferenceTrajectory
from uavsim.vehicles.params import VehicleParams

StateSource = Literal["truth", "estimate"]


def _segment_to_point(
    p0: np.ndarray,
    p1: np.ndarray,
    *,
    t0: float,
    horizon_s: float,
    sample_dt_s: float,
    yaw_rad: float,
) -> SampledReference:
    """Linear position segment with constant velocity and fixed yaw."""
    horizon_s = max(float(horizon_s), float(sample_dt_s))
    n = max(int(np.ceil(horizon_s / sample_dt_s)) + 1, 2)
    t_grid = np.linspace(t0, t0 + horizon_s, n)
    p0 = np.asarray(p0, dtype=float).reshape(3)
    p1 = np.asarray(p1, dtype=float).reshape(3)
    v = (p1 - p0) / horizon_s
    x_grid = np.zeros((n, STATE_DIM), dtype=float)
    for i, ti in enumerate(t_grid):
        alpha = (float(ti) - t0) / horizon_s
        x_grid[i, 0:3] = (1.0 - alpha) * p0 + alpha * p1
        x_grid[i, 5] = yaw_rad
        x_grid[i, 6:9] = v
    ref = SampledReference(
        t0=float(t_grid[0]),
        tf=float(t_grid[-1]),
        backend_id="intercept_pursue",
        metadata={"kind": "lead_segment", "horizon_s": horizon_s},
        t_grid=t_grid,
        x_grid=x_grid,
    )
    return ref


class InterceptPursueGuidance:
    """
    Backend id ``intercept_pursue``.

    Offline ``plan``: seed climb / takeoff reference (waypoints).
    Online ``update``: constant-velocity lead point on a scripted target path,
    rebuild short-horizon ownship ``SampledReference``.
    """

    id = "intercept_pursue"

    def __init__(
        self,
        *,
        replan_period_s: float = 0.2,
        replan_start_s: float = 2.5,
        lead_time_s: float = 1.5,
        capture_radius_m: float = 1.0,
        horizon_s: float = 3.0,
        sample_dt_s: float = 0.01,
        seed_method: Literal["auto", "interp", "minsnap"] = "minsnap",
        yaw_mode: Literal["constant", "path_tangent", "from_waypoints"] = "from_waypoints",
        state_source: StateSource = "truth",
        fail_on_infeasible: bool = False,
    ) -> None:
        self.replan_period_s = float(replan_period_s)
        self.replan_start_s = float(replan_start_s)
        self.lead_time_s = float(lead_time_s)
        self.capture_radius_m = float(capture_radius_m)
        self.horizon_s = float(horizon_s)
        self.sample_dt_s = float(sample_dt_s)
        self.state_source = state_source
        self.fail_on_infeasible = fail_on_infeasible
        self._seed_wp = WaypointsGuidance(
            method=seed_method,
            yaw_mode=yaw_mode,
            sample_dt_s=sample_dt_s,
            fail_on_infeasible=fail_on_infeasible,
        )
        self._target_wp = WaypointsGuidance(
            method="interp",
            yaw_mode="from_waypoints",
            sample_dt_s=sample_dt_s,
            fail_on_infeasible=False,
        )
        self.target_reference: ReferenceTrajectory | None = None
        self.captured: bool = False
        self.mission_tf: float = 10.0
        self.replan_count: int = 0

    def plan(
        self,
        mission: dict[str, Any],
        vehicle: VehicleParams,
        *,
        rng: Any | None = None,
    ) -> PlanResult:
        _ = rng
        seed_file = mission.get("seed_mission_file") or mission.get("mission_file")
        target_file = mission.get("target_mission_file")
        if not seed_file or not target_file:
            msg = "intercept_pursue requires seed_mission_file and target_mission_file"
            raise ValueError(msg)

        seed_plan = self._seed_wp.plan({"mission_file": str(seed_file)}, vehicle)
        tgt_plan = self._target_wp.plan({"mission_file": str(target_file)}, vehicle)
        self.target_reference = tgt_plan.reference
        self.captured = False
        self.replan_count = 0
        self.mission_tf = float(
            mission.get("duration_s", max(seed_plan.reference.tf, tgt_plan.reference.tf))
        )
        # Stretch seed ref to mission_tf if needed by holding final pose
        ref = seed_plan.reference
        if ref.tf < self.mission_tf - 1e-9 and isinstance(ref, SampledReference):
            x_end = ref.evaluate(ref.tf).x_ref.copy()
            t_extra = np.arange(
                ref.tf + self.sample_dt_s, self.mission_tf + 1e-12, self.sample_dt_s
            )
            if t_extra.size:
                t_grid = np.concatenate([ref.t_grid, t_extra])
                x_extra = np.tile(x_end, (t_extra.size, 1))
                x_grid = np.vstack([ref.x_grid, x_extra])
                ref = SampledReference(
                    t0=float(t_grid[0]),
                    tf=float(t_grid[-1]),
                    backend_id=self.id,
                    metadata={**ref.metadata, "extended_hold": True},
                    t_grid=t_grid,
                    x_grid=x_grid,
                )
        elif ref.tf < self.mission_tf - 1e-9:
            # HoldReference or other: re-plan not extended; clamp mission_tf
            self.mission_tf = float(ref.tf)

        feas = check_reference_feasibility(ref, vehicle)
        diag = {
            "seed": seed_plan.diagnostics,
            "target_tf": float(tgt_plan.reference.tf),
            "mission_tf": self.mission_tf,
            "replan_period_s": self.replan_period_s,
            "lead_time_s": self.lead_time_s,
            "capture_radius_m": self.capture_radius_m,
        }
        return PlanResult(reference=ref, feasibility=feas, diagnostics=diag)

    def update(
        self,
        state: Any,
        t: float,
        mission: dict[str, Any],
        vehicle: VehicleParams,
        reference: ReferenceTrajectory,
        *,
        rng: Any | None = None,
    ) -> PlanResult | None:
        _ = mission, rng, reference
        if self.target_reference is None:
            return None

        x = np.asarray(state, dtype=float).reshape(STATE_DIM)
        p = x[0:3].copy()
        t = float(t)
        if t >= self.mission_tf - 1e-12:
            return None
        # Stay on seed climb until replan_start (pad / GE phase)
        if t + 1e-12 < self.replan_start_s:
            return None

        tgt_s = self.target_reference.evaluate(t)
        p_t = tgt_s.x_ref[0:3].copy()
        v_t = tgt_s.x_ref[6:9].copy()
        # Prefer a_ref velocity from finite difference if nearly zero
        if float(np.linalg.norm(v_t)) < 1e-6:
            dt = 0.05
            p_t2 = self.target_reference.evaluate(min(t + dt, self.target_reference.tf)).x_ref[0:3]
            v_t = (p_t2 - p_t) / dt

        range_m = float(np.linalg.norm(p - p_t))
        if range_m <= self.capture_radius_m:
            self.captured = True

        if self.captured:
            # Track target position open-loop for remainder
            p_star = p_t
            horizon = min(self.horizon_s, max(self.mission_tf - t, self.sample_dt_s))
        else:
            p_star = predict_constant_velocity(p_t, v_t, self.lead_time_s)
            horizon = min(self.horizon_s, max(self.mission_tf - t, self.sample_dt_s))

        # Yaw: face horizontal intercept direction
        dxy = p_star[0:2] - p[0:2]
        if float(np.linalg.norm(dxy)) > 1e-6:
            yaw = float(np.arctan2(dxy[1], dxy[0]))
        else:
            yaw = float(x[5])

        new_ref = _segment_to_point(
            p,
            p_star,
            t0=t,
            horizon_s=horizon,
            sample_dt_s=self.sample_dt_s,
            yaw_rad=yaw,
        )
        # Extend hold at end of segment through mission_tf so adapter always has valid tf
        if new_ref.tf < self.mission_tf - 1e-9:
            x_end = new_ref.evaluate(new_ref.tf).x_ref.copy()
            t_extra = np.arange(
                new_ref.tf + self.sample_dt_s, self.mission_tf + 1e-12, self.sample_dt_s
            )
            if t_extra.size:
                t_grid = np.concatenate([new_ref.t_grid, t_extra])
                x_extra = np.tile(x_end, (t_extra.size, 1))
                x_grid = np.vstack([new_ref.x_grid, x_extra])
                new_ref = SampledReference(
                    t0=float(t_grid[0]),
                    tf=float(t_grid[-1]),
                    backend_id=self.id,
                    metadata={
                        **new_ref.metadata,
                        "captured": self.captured,
                        "p_star": p_star.tolist(),
                        "range_m": range_m,
                    },
                    t_grid=t_grid,
                    x_grid=x_grid,
                )

        self.replan_count += 1
        feas = check_reference_feasibility(new_ref, vehicle)
        return PlanResult(
            reference=new_ref,
            feasibility=feas,
            diagnostics={
                "t": t,
                "range_m": range_m,
                "captured": self.captured,
                "p_star": p_star.tolist(),
                "replan_count": self.replan_count,
            },
        )


register_guidance("intercept_pursue", InterceptPursueGuidance)
