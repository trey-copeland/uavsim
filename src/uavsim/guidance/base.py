"""Guidance backend protocol and registry."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from uavsim.reference import FeasibilityReport, ReferenceTrajectory
from uavsim.vehicles.params import VehicleParams


@dataclass
class PlanResult:
    reference: ReferenceTrajectory
    feasibility: FeasibilityReport
    diagnostics: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class GuidanceBackend(Protocol):
    id: str

    def plan(
        self,
        mission: dict[str, Any],
        vehicle: VehicleParams,
        *,
        rng: Any | None = None,
    ) -> PlanResult:
        """Offline plan: mission + vehicle → reference + feasibility."""
        ...

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
        """Optional in-loop replan; core backends return None."""
        ...


_REGISTRY: dict[str, type] = {}


def register_guidance(backend_id: str, cls: type) -> None:
    _REGISTRY[backend_id] = cls


def get_guidance_class(backend_id: str) -> type:
    if backend_id not in _REGISTRY:
        known = ", ".join(sorted(_REGISTRY)) or "(none)"
        msg = f"Unknown guidance backend {backend_id!r}. Known: {known}"
        raise KeyError(msg)
    return _REGISTRY[backend_id]


def list_guidance_backends() -> list[str]:
    return sorted(_REGISTRY)


def create_guidance(backend_id: str, **kwargs: Any) -> GuidanceBackend:
    cls = get_guidance_class(backend_id)
    return cls(**kwargs)  # type: ignore[call-arg]
