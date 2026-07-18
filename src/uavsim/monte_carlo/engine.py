"""Local Monte Carlo engine (trial loop + summary)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from uavsim.monte_carlo.perturb import PerturbationSpec, perturb_vehicle
from uavsim.monte_carlo.summary import summarize_trials
from uavsim.vehicles.params import VehicleParams


@dataclass
class MonteCarloResult:
    trials: list[dict[str, Any]] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)
    redesign_controller: bool = False


def run_monte_carlo(
    *,
    nominal_vehicle: VehicleParams,
    base_seed: int,
    n_trials: int,
    trial_fn: Callable[[int, VehicleParams, dict[str, float]], dict[str, Any]],
    spec: PerturbationSpec | None = None,
    redesign_controller: bool = False,
    trial_ids: range | list[int] | None = None,
) -> MonteCarloResult:
    """
    Run MC trials.

    ``trial_fn(trial_id, plant_vehicle, param_dict) -> metrics row`` must be
    deterministic given those inputs (and fixed controller/reference outside).
    """
    if n_trials < 1:
        msg = "n_trials must be >= 1"
        raise ValueError(msg)

    ids = list(trial_ids) if trial_ids is not None else list(range(n_trials))
    trials: list[dict[str, Any]] = []
    for trial_id in ids:
        plant, params = perturb_vehicle(
            nominal_vehicle,
            base_seed=base_seed,
            trial_id=int(trial_id),
            spec=spec,
        )
        row = trial_fn(int(trial_id), plant, params)
        row = {
            "trial_id": int(trial_id),
            "base_seed": int(base_seed),
            **params,
            **row,
        }
        trials.append(row)

    # Stable order by trial_id for merge-friendliness
    trials.sort(key=lambda r: int(r["trial_id"]))
    summary = summarize_trials(trials)
    summary["redesign_controller"] = redesign_controller
    summary["base_seed"] = int(base_seed)
    return MonteCarloResult(
        trials=trials,
        summary=summary,
        redesign_controller=redesign_controller,
    )
