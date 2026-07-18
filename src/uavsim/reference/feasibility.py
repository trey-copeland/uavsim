"""Trajectory feasibility checks (operate on reference grids / trajectories)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from uavsim.reference.types import ReferenceTrajectory, SampledReference
from uavsim.vehicles.params import VehicleParams


@dataclass
class FeasibilityIssue:
    code: str
    severity: str  # "warn" | "fail"
    message: str
    value: float | None = None
    limit: float | None = None


@dataclass
class FeasibilityReport:
    ok: bool
    issues: list[FeasibilityIssue] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "issues": [
                {
                    "code": i.code,
                    "severity": i.severity,
                    "message": i.message,
                    "value": i.value,
                    "limit": i.limit,
                }
                for i in self.issues
            ],
            "summary": self.summary,
        }


@dataclass
class FeasibilityLimits:
    """Warn/fail thresholds for pre-sim reference checks."""

    attitude_warn_rad: float = np.deg2rad(15.0)
    attitude_fail_rad: float = np.deg2rad(30.0)
    velocity_warn_m_s: float = 3.0
    velocity_fail_m_s: float = 8.0
    yaw_rate_warn_rad_s: float = np.deg2rad(50.0)
    yaw_rate_fail_rad_s: float = np.deg2rad(100.0)
    yaw_rate_rms_warn_rad_s: float = np.deg2rad(20.0)
    max_tilt_for_accel_rad: float = np.deg2rad(30.0)
    yaw_accel_margin: float = 0.7  # fraction of τ_max / Izz


def check_sampled_feasibility(
    reference: SampledReference,
    vehicle: VehicleParams,
    limits: FeasibilityLimits | None = None,
) -> FeasibilityReport:
    """Run heritage-inspired feasibility checks on a sampled reference."""
    limits = limits or FeasibilityLimits()
    issues: list[FeasibilityIssue] = []
    x = reference.x_grid
    t = reference.t_grid

    pos = x[:, 0:3]
    euler = x[:, 3:6]
    vel = x[:, 6:9]
    # Approximate accel from velocity
    if t.size >= 2:
        acc = np.gradient(vel, t, axis=0)
        yaw_rate = np.gradient(euler[:, 2], t)
        yaw_accel = np.gradient(yaw_rate, t)
    else:
        acc = np.zeros_like(vel)
        yaw_rate = np.zeros(t.size)
        yaw_accel = np.zeros(t.size)

    max_roll = float(np.max(np.abs(euler[:, 0])))
    max_pitch = float(np.max(np.abs(euler[:, 1])))
    max_tilt = float(max(max_roll, max_pitch))
    max_speed = float(np.max(np.linalg.norm(vel, axis=1)))
    max_horiz_accel = float(np.max(np.linalg.norm(acc[:, 0:2], axis=1)))
    max_yaw_rate = float(np.max(np.abs(yaw_rate)))
    rms_yaw_rate = float(np.sqrt(np.mean(yaw_rate**2)))
    max_yaw_accel = float(np.max(np.abs(yaw_accel)))

    g = vehicle.gravity_m_s2
    a_safe = g * np.tan(limits.max_tilt_for_accel_rad)
    yaw_accel_phys = vehicle.limits.torque_max_nm / vehicle.inertia.izz_kg_m2
    yaw_accel_limit = limits.yaw_accel_margin * yaw_accel_phys

    if max_tilt > limits.attitude_fail_rad:
        issues.append(
            FeasibilityIssue(
                code="attitude_peak",
                severity="fail",
                message=(
                    f"Peak feedforward attitude {np.rad2deg(max_tilt):.1f}° exceeds "
                    f"fail limit {np.rad2deg(limits.attitude_fail_rad):.1f}°."
                ),
                value=max_tilt,
                limit=limits.attitude_fail_rad,
            )
        )
    elif max_tilt > limits.attitude_warn_rad:
        issues.append(
            FeasibilityIssue(
                code="attitude_peak",
                severity="warn",
                message=(
                    f"Peak feedforward attitude {np.rad2deg(max_tilt):.1f}° exceeds "
                    f"warn limit {np.rad2deg(limits.attitude_warn_rad):.1f}°."
                ),
                value=max_tilt,
                limit=limits.attitude_warn_rad,
            )
        )

    if max_speed > limits.velocity_fail_m_s:
        issues.append(
            FeasibilityIssue(
                code="velocity_peak",
                severity="fail",
                message=f"Peak speed {max_speed:.2f} m/s exceeds fail limit.",
                value=max_speed,
                limit=limits.velocity_fail_m_s,
            )
        )
    elif max_speed > limits.velocity_warn_m_s:
        issues.append(
            FeasibilityIssue(
                code="velocity_peak",
                severity="warn",
                message=f"Peak speed {max_speed:.2f} m/s is aggressive for this vehicle class.",
                value=max_speed,
                limit=limits.velocity_warn_m_s,
            )
        )

    if max_horiz_accel > a_safe:
        issues.append(
            FeasibilityIssue(
                code="horizontal_accel",
                severity="warn",
                message=(
                    f"Peak horizontal accel {max_horiz_accel:.2f} m/s² may require "
                    f">{np.rad2deg(limits.max_tilt_for_accel_rad):.0f}° tilt "
                    f"(safe ≈ {a_safe:.2f} m/s²)."
                ),
                value=max_horiz_accel,
                limit=float(a_safe),
            )
        )

    if max_yaw_rate > limits.yaw_rate_fail_rad_s:
        issues.append(
            FeasibilityIssue(
                code="yaw_rate_peak",
                severity="fail",
                message=(
                    f"Peak yaw rate {np.rad2deg(max_yaw_rate):.1f} °/s exceeds critical limit "
                    f"{np.rad2deg(limits.yaw_rate_fail_rad_s):.1f} °/s "
                    "(often caused by path-tangent auto-yaw on tight curves)."
                ),
                value=max_yaw_rate,
                limit=limits.yaw_rate_fail_rad_s,
            )
        )
    elif max_yaw_rate > limits.yaw_rate_warn_rad_s:
        issues.append(
            FeasibilityIssue(
                code="yaw_rate_peak",
                severity="warn",
                message=(
                    f"Peak yaw rate {np.rad2deg(max_yaw_rate):.1f} °/s is high for LQR tracking."
                ),
                value=max_yaw_rate,
                limit=limits.yaw_rate_warn_rad_s,
            )
        )

    if rms_yaw_rate > limits.yaw_rate_rms_warn_rad_s:
        issues.append(
            FeasibilityIssue(
                code="yaw_rate_rms",
                severity="warn",
                message=(
                    f"RMS yaw rate {np.rad2deg(rms_yaw_rate):.1f} °/s is sustained-high "
                    "(consider constant yaw)."
                ),
                value=rms_yaw_rate,
                limit=limits.yaw_rate_rms_warn_rad_s,
            )
        )

    if max_yaw_accel > yaw_accel_limit:
        issues.append(
            FeasibilityIssue(
                code="yaw_accel",
                severity="warn",
                message=(
                    f"Peak yaw accel {max_yaw_accel:.2f} rad/s² exceeds "
                    f"{limits.yaw_accel_margin:.0%} of τ_max/Izz ({yaw_accel_limit:.2f})."
                ),
                value=max_yaw_accel,
                limit=float(yaw_accel_limit),
            )
        )

    # Path length / duration sanity
    path_len = float(np.sum(np.linalg.norm(np.diff(pos, axis=0), axis=1))) if t.size >= 2 else 0.0

    summary = {
        "max_roll_rad": max_roll,
        "max_pitch_rad": max_pitch,
        "max_tilt_rad": max_tilt,
        "max_speed_m_s": max_speed,
        "max_horiz_accel_m_s2": max_horiz_accel,
        "max_yaw_rate_rad_s": max_yaw_rate,
        "rms_yaw_rate_rad_s": rms_yaw_rate,
        "max_yaw_accel_rad_s2": max_yaw_accel,
        "path_length_m": path_len,
        "duration_s": float(t[-1] - t[0]) if t.size else 0.0,
        "n_samples": int(t.size),
    }
    has_fail = any(i.severity == "fail" for i in issues)
    return FeasibilityReport(ok=not has_fail, issues=issues, summary=summary)


def check_reference_feasibility(
    reference: ReferenceTrajectory,
    vehicle: VehicleParams,
    limits: FeasibilityLimits | None = None,
    *,
    sample_dt_s: float = 0.01,
) -> FeasibilityReport:
    """Feasibility for any reference by dense sampling if needed."""
    if isinstance(reference, SampledReference):
        return check_sampled_feasibility(reference, vehicle, limits)

    t0, tf = reference.t0, reference.tf
    if tf <= t0:
        return FeasibilityReport(
            ok=True,
            issues=[],
            summary={"duration_s": 0.0, "n_samples": 0},
        )
    n = max(int(np.ceil((tf - t0) / sample_dt_s)) + 1, 2)
    t = np.linspace(t0, tf, n)
    x = np.vstack([reference.evaluate(float(ti)).x_ref for ti in t])
    sampled = SampledReference(
        t0=t0,
        tf=tf,
        backend_id=reference.backend_id,
        metadata=dict(reference.metadata),
        t_grid=t,
        x_grid=x,
    )
    return check_sampled_feasibility(sampled, vehicle, limits)
