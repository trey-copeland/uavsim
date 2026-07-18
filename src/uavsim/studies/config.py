"""Study configuration models and loading."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Literal

import numpy as np
import yaml
from pydantic import BaseModel, ConfigDict, Field

from uavsim.dynamics import STATE_DIM


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


class StudyConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1
    study_id: str
    seed: int = 0
    vehicle: str
    controller: ControllerConfig
    guidance: HoldGuidanceConfig
    sim: SimConfig = Field(default_factory=SimConfig)
    metrics: MetricsConfig = Field(default_factory=MetricsConfig)
    initial_state: InitialStateConfig | None = None


def _resolve_path(path: str | Path, base: Path) -> Path:
    p = Path(path)
    if p.is_absolute():
        return p
    # Prefer CWD-relative, then study-file relative
    cwd_candidate = Path.cwd() / p
    if cwd_candidate.exists():
        return cwd_candidate.resolve()
    return (base / p).resolve()


def load_study(path: str | Path) -> tuple[StudyConfig, Path, str]:
    """Return (config, resolved vehicle path, config content hash)."""
    path = Path(path).resolve()
    raw = path.read_text(encoding="utf-8")
    data = yaml.safe_load(raw)
    cfg = StudyConfig.model_validate(data)
    vehicle_path = _resolve_path(cfg.vehicle, path.parent)
    cfg_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    return cfg, vehicle_path, cfg_hash
