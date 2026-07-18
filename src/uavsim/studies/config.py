"""Study configuration models and loading."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Annotated, Any, Literal

import numpy as np
import yaml
from pydantic import BaseModel, ConfigDict, Field

from uavsim.dynamics import STATE_DIM
from uavsim.monte_carlo import PerturbationSpec


class ControllerConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["lqr_hover"] = "lqr_hover"
    Q_diag: list[float] = Field(min_length=12, max_length=12)
    R_diag: list[float] = Field(min_length=4, max_length=4)


class HoldGuidanceConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["hold"] = "hold"
    position_ned_m: list[float] = Field(min_length=3, max_length=3)
    yaw_rad: float = 0.0
    duration_s: float = Field(gt=0, default=5.0)


class WaypointsGuidanceConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["waypoints"] = "waypoints"
    mission_file: str
    method: Literal["auto", "interp", "minsnap"] = "auto"
    yaw_mode: Literal["constant", "path_tangent", "from_waypoints"] = "constant"
    sample_dt_s: float = Field(gt=0, default=0.01)
    fail_on_infeasible: bool = False


GuidanceConfig = Annotated[
    HoldGuidanceConfig | WaypointsGuidanceConfig,
    Field(discriminator="type"),
]


class SimConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dt_s: float = Field(gt=0, default=0.01)
    method: str = "rk45"
    rtol: float = 1e-6
    atol: float = 1e-8


class MetricsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    position_bound_m: float = Field(gt=0, default=0.1)


class InitialStateConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    position_ned_m: list[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0])
    euler_rad: list[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0])
    velocity_ned_m_s: list[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0])
    omega_body_rad_s: list[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0])

    def to_array(self) -> np.ndarray:
        x = np.zeros(STATE_DIM)
        x[0:3] = self.position_ned_m
        x[3:6] = self.euler_rad
        x[6:9] = self.velocity_ned_m_s
        x[9:12] = self.omega_body_rad_s
        return x


class MonteCarloConfig(BaseModel):
    """MC block. When enabled, ``uavsim study`` runs N perturbed trials."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    n_trials: int = Field(default=20, ge=1)
    backend: Literal["local", "docker"] = "local"
    shards: int = Field(default=1, ge=1)
    # Heritage default: design controller on nominal; plant is perturbed
    redesign_controller: bool = False
    mass_rel_sigma: float = Field(default=0.05, ge=0)
    inertia_rel_sigma: float = Field(default=0.075, ge=0)
    arm_rel_sigma: float = Field(default=0.02, ge=0)

    def perturbation_spec(self) -> PerturbationSpec:
        return PerturbationSpec(
            mass_rel_sigma=self.mass_rel_sigma,
            inertia_rel_sigma=self.inertia_rel_sigma,
            arm_rel_sigma=self.arm_rel_sigma,
        )


class StudyConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1
    study_id: str
    seed: int = 0
    vehicle: str
    controller: ControllerConfig
    guidance: GuidanceConfig
    sim: SimConfig = Field(default_factory=SimConfig)
    metrics: MetricsConfig = Field(default_factory=MetricsConfig)
    initial_state: InitialStateConfig | None = None
    monte_carlo: MonteCarloConfig = Field(default_factory=MonteCarloConfig)


def _resolve_path(path: str | Path, base: Path) -> Path:
    p = Path(path)
    if p.is_absolute():
        return p
    # Prefer CWD-relative, then study-file relative
    cwd_candidate = Path.cwd() / p
    if cwd_candidate.exists():
        return cwd_candidate.resolve()
    return (base / p).resolve()


def load_study(path: str | Path) -> tuple[StudyConfig, Path, str, Path | None]:
    """Return (config, vehicle path, config hash, resolved mission path or None)."""
    path = Path(path).resolve()
    raw = path.read_text(encoding="utf-8")
    data = yaml.safe_load(raw)
    cfg = StudyConfig.model_validate(data)
    vehicle_path = _resolve_path(cfg.vehicle, path.parent)
    mission_path: Path | None = None
    if isinstance(cfg.guidance, WaypointsGuidanceConfig):
        mission_path = _resolve_path(cfg.guidance.mission_file, path.parent)
        # Rewrite so pipeline can open a real path
        cfg.guidance.mission_file = str(mission_path)
    cfg_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    return cfg, vehicle_path, cfg_hash, mission_path


def guidance_mission_dict(cfg: StudyConfig) -> dict[str, Any]:
    """Build the mission dict passed to GuidanceBackend.plan."""
    g = cfg.guidance
    if isinstance(g, HoldGuidanceConfig):
        return {
            "position_ned_m": g.position_ned_m,
            "yaw_rad": g.yaw_rad,
            "duration_s": g.duration_s,
        }
    if isinstance(g, WaypointsGuidanceConfig):
        return {"mission_file": g.mission_file}
    msg = f"Unsupported guidance config type: {type(g)}"
    raise TypeError(msg)
