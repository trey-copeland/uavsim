"""Guidance backends (planners) producing reference trajectories."""

from uavsim.guidance import hold as _hold  # noqa: F401 — register hold
from uavsim.guidance.base import (
    GuidanceBackend,
    PlanResult,
    create_guidance,
    list_guidance_backends,
    register_guidance,
)
from uavsim.guidance.hold import HoldGuidance
from uavsim.guidance.waypoints import WaypointsGuidance, load_mission
from uavsim.guidance.waypoints import backend as _wp_backend  # noqa: F401 — register

__all__ = [
    "GuidanceBackend",
    "HoldGuidance",
    "PlanResult",
    "WaypointsGuidance",
    "create_guidance",
    "list_guidance_backends",
    "load_mission",
    "register_guidance",
]
