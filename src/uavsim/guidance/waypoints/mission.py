"""Waypoint mission load / schema (YAML or JSON .wpt)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Waypoint(BaseModel):
    model_config = ConfigDict(extra="ignore")

    time: float = Field(ge=0)
    x: float
    y: float
    z: float
    yaw: float | None = None  # None / null → auto when yaw_mode allows
    label: str | None = None
    # Optional velocity/accel for minsnap (m/s, m/s²)
    vx: float | None = None
    vy: float | None = None
    vz: float | None = None
    ax: float | None = None
    ay: float | None = None
    az: float | None = None


class WaypointMission(BaseModel):
    model_config = ConfigDict(extra="ignore")

    schema_version: int = 1
    name: str = "unnamed"
    description: str = ""
    frame: str = "NED"
    waypoints: list[Waypoint] = Field(min_length=2)

    @field_validator("frame")
    @classmethod
    def frame_must_be_ned(cls, v: str) -> str:
        if v.upper() != "NED":
            msg = f"Only NED missions supported in core; got frame={v!r}"
            raise ValueError(msg)
        return "NED"

    @model_validator(mode="after")
    def times_strictly_increasing(self) -> WaypointMission:
        times = [w.time for w in self.waypoints]
        if any(times[i + 1] <= times[i] for i in range(len(times) - 1)):
            msg = "Waypoint times must be strictly increasing"
            raise ValueError(msg)
        return self

    @property
    def time(self) -> np.ndarray:
        return np.array([w.time for w in self.waypoints], dtype=float)

    @property
    def position(self) -> np.ndarray:
        return np.array([[w.x, w.y, w.z] for w in self.waypoints], dtype=float)

    @property
    def yaw(self) -> np.ndarray:
        """Yaw array; NaN marks auto-from-path when policy requests it."""
        out = np.empty(len(self.waypoints), dtype=float)
        for i, w in enumerate(self.waypoints):
            out[i] = np.nan if w.yaw is None else float(w.yaw)
        return out

    def velocity_specified(self) -> tuple[np.ndarray, np.ndarray]:
        """Return (vel Nx3, mask N bool) — mask True where user specified any component."""
        n = len(self.waypoints)
        vel = np.zeros((n, 3), dtype=float)
        mask = np.zeros(n, dtype=bool)
        for i, w in enumerate(self.waypoints):
            if w.vx is not None or w.vy is not None or w.vz is not None:
                mask[i] = True
                vel[i, 0] = 0.0 if w.vx is None else w.vx
                vel[i, 1] = 0.0 if w.vy is None else w.vy
                vel[i, 2] = 0.0 if w.vz is None else w.vz
        # Start/end always treated as specified zero if not set (minsnap BC)
        if not mask[0]:
            mask[0] = True
        if not mask[-1]:
            mask[-1] = True
        return vel, mask

    def acceleration_specified(self) -> tuple[np.ndarray, np.ndarray]:
        n = len(self.waypoints)
        acc = np.zeros((n, 3), dtype=float)
        mask = np.zeros(n, dtype=bool)
        for i, w in enumerate(self.waypoints):
            if w.ax is not None or w.ay is not None or w.az is not None:
                mask[i] = True
                acc[i, 0] = 0.0 if w.ax is None else w.ax
                acc[i, 1] = 0.0 if w.ay is None else w.ay
                acc[i, 2] = 0.0 if w.az is None else w.az
        if not mask[0]:
            mask[0] = True
        if not mask[-1]:
            mask[-1] = True
        return acc, mask


def _normalize_raw(data: dict[str, Any]) -> dict[str, Any]:
    """Accept heritage .wpt shape (metadata + waypoints) and flat YAML."""
    if "waypoints" not in data:
        msg = "Mission file must contain a 'waypoints' list"
        raise ValueError(msg)

    meta = data.get("metadata") or {}
    name = data.get("name") or meta.get("name") or "unnamed"
    description = data.get("description") or meta.get("description") or ""
    frame = data.get("frame") or meta.get("frame") or "NED"
    schema_version = int(data.get("schema_version", meta.get("schema_version", 1)))

    wps: list[dict[str, Any]] = []
    for item in data["waypoints"]:
        if not isinstance(item, dict):
            msg = f"Waypoint entries must be mappings, got {type(item)}"
            raise TypeError(msg)
        wps.append(item)

    return {
        "schema_version": schema_version,
        "name": name,
        "description": description,
        "frame": frame,
        "waypoints": wps,
    }


def load_mission(path: str | Path) -> WaypointMission:
    path = Path(path)
    if not path.is_file():
        msg = f"Mission file not found: {path}"
        raise FileNotFoundError(msg)

    text = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()
    raw = json.loads(text) if suffix in {".json", ".wpt"} else yaml.safe_load(text)

    if not isinstance(raw, dict):
        msg = f"Mission root must be a mapping: {path}"
        raise ValueError(msg)

    return WaypointMission.model_validate(_normalize_raw(raw))
