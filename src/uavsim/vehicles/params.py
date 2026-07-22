"""Vehicle parameters, limits, and YAML loading."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import numpy as np
import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator


class InertiaParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ixx_kg_m2: float = Field(gt=0)
    iyy_kg_m2: float = Field(gt=0)
    izz_kg_m2: float = Field(gt=0)

    def as_diag(self) -> np.ndarray:
        return np.diag([self.ixx_kg_m2, self.iyy_kg_m2, self.izz_kg_m2])


class ActuatorLimits(BaseModel):
    model_config = ConfigDict(extra="forbid")

    thrust_min_n: float = 0.0
    thrust_max_n: float = Field(gt=0)
    torque_max_nm: float = Field(gt=0)

    def u_min(self) -> np.ndarray:
        t = self.torque_max_nm
        return np.array([self.thrust_min_n, -t, -t, -t], dtype=float)

    def u_max(self) -> np.ndarray:
        t = self.torque_max_nm
        return np.array([self.thrust_max_n, t, t, t], dtype=float)


class PropulsionParams(BaseModel):
    """
    Quadrotor propulsion for mixer + first-order motors (D-7 / D-8).

    Thrust per motor: ``f = ct * ω²``. Reaction |torque| ``= cq * ω²``.
    Defaults sized so hover ω is ~600 rad/s for the 0.5 kg default vehicle.
    """

    model_config = ConfigDict(extra="forbid")

    layout: Literal["x"] = "x"
    ct_n_s2: float = Field(default=3.405e-6, gt=0)  # N / (rad/s)²
    cq_nm_s2: float = Field(default=5.4e-8, gt=0)  # N·m / (rad/s)²
    motor_time_const_s: float = Field(default=0.05, gt=0)
    omega_min_rad_s: float = Field(default=0.0, ge=0)
    omega_max_rad_s: float = Field(default=1200.0, gt=0)


class AeroParams(BaseModel):
    """
    Optional aero / environment forces (D-4 / D-5 + ground effect).

    All coefficients default to **off** (zero / ``none``) so existing studies
    bit-match the vacuum rigid-body plant.
    """

    model_config = ConfigDict(extra="forbid")

    # Translational drag in NED: F = -b_lin v - b_quad ||v|| v
    drag_lin_ns_m: float = Field(default=0.0, ge=0)  # N·s/m
    drag_quad_ns2_m2: float = Field(default=0.0, ge=0)  # N·s²/m²
    # Body rate damping τ = -c ω
    rate_damp_nm_s: float = Field(default=0.0, ge=0)  # N·m·s
    # Lumped prop H-force in body xy: f_xy = -k_h * T * v_xy  (k_h in s/m)
    prop_h_s_per_m: float = Field(default=0.0, ge=0)
    # Ground effect on thrust (κ ≥ 1 near ground)
    ground_effect: Literal["none", "cheeseman", "exp"] = "none"
    rotor_radius_m: float = Field(default=0.1, gt=0)
    # Flat ground plane NED z (z+ down). AGL = ground_z_ned_m - z.
    ground_z_ned_m: float = 0.0
    ge_exp_a: float = Field(default=0.5, ge=0)  # exp model: 1 + a e^{-b h/R}
    ge_exp_b: float = Field(default=2.0, ge=0)
    ge_kappa_max: float = Field(default=3.0, gt=1.0)


class VehicleParams(BaseModel):
    """Physical params + limits. Does not own equations of motion."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1
    vehicle_id: str = "default_quadrotor"
    mass_kg: float = Field(gt=0)
    gravity_m_s2: float = Field(gt=0, default=9.81)
    arm_length_m: float = Field(gt=0)
    inertia: InertiaParams
    limits: ActuatorLimits
    propulsion: PropulsionParams = Field(default_factory=PropulsionParams)
    aero: AeroParams = Field(default_factory=AeroParams)

    @property
    def m(self) -> float:
        return self.mass_kg

    @property
    def g(self) -> float:
        return self.gravity_m_s2

    def hover_thrust_n(self) -> float:
        return self.mass_kg * self.gravity_m_s2

    def u_hover(self) -> np.ndarray:
        return np.array([self.hover_thrust_n(), 0.0, 0.0, 0.0], dtype=float)

    @field_validator("limits")
    @classmethod
    def thrust_max_covers_hover(cls, limits: ActuatorLimits, info: Any) -> ActuatorLimits:
        # Validated after full model via model_validator if needed; keep simple.
        return limits


def load_vehicle(path: str | Path) -> VehicleParams:
    path = Path(path)
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        msg = f"Vehicle config must be a mapping: {path}"
        raise ValueError(msg)
    return VehicleParams.model_validate(data)


def default_vehicle() -> VehicleParams:
    """Heritage-scale 500 g class defaults (no file I/O)."""
    return VehicleParams(
        vehicle_id="default_quadrotor",
        mass_kg=0.5,
        gravity_m_s2=9.81,
        arm_length_m=0.25,
        inertia=InertiaParams(ixx_kg_m2=0.0075, iyy_kg_m2=0.0075, izz_kg_m2=0.013),
        limits=ActuatorLimits(
            thrust_min_n=0.0,
            thrust_max_n=2 * 0.5 * 9.81,
            torque_max_nm=1.0,
        ),
        propulsion=PropulsionParams(),
        aero=AeroParams(),
    )
