"""Reference trajectories: types, evaluation, feasibility (no planners)."""

from uavsim.reference.attitude import body_rates_from_euler, feedforward_roll_pitch
from uavsim.reference.feasibility import (
    FeasibilityIssue,
    FeasibilityLimits,
    FeasibilityReport,
    check_reference_feasibility,
    check_sampled_feasibility,
)
from uavsim.reference.types import (
    HoldReference,
    ReferenceSample,
    ReferenceTrajectory,
    SampledReference,
    hold_at_ned,
    pack_state_grid,
)

__all__ = [
    "FeasibilityIssue",
    "FeasibilityLimits",
    "FeasibilityReport",
    "HoldReference",
    "ReferenceSample",
    "ReferenceTrajectory",
    "SampledReference",
    "body_rates_from_euler",
    "check_reference_feasibility",
    "check_sampled_feasibility",
    "feedforward_roll_pitch",
    "hold_at_ned",
    "pack_state_grid",
]
