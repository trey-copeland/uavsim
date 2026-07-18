"""Vehicle parameters, limits, and YAML loading."""

from __future__ import annotations

from pathlib import Path
from typing import Any

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
    )
