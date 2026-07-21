"""Local Monte Carlo engine (trial loop + summary)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from uavsim.monte_carlo.perturb import PerturbationSpec, perturb_vehicle
from uavsim.monte_carlo.progress import McProgressBar
from uavsim.monte_carlo.summary import summarize_trials
from uavsim.vehicles.params import VehicleParams

# progress_fn(completed, total, trial_id, row) after each trial
ProgressFn = Callable[[int, int, int, dict[str, Any]], None]


@dataclass
class MonteCarloResult:
    trials: list[dict[str, Any]] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)
    redesign_controller: bool = False


def default_mc_progress(completed: int, total: int, trial_id: int, row: dict[str, Any]) -> None:
    """Simple fallback: multi-line log (used if bar not constructed)."""
    ok = row.get("success")
    rmse = row.get("rmse_position_m")
    rmse_s = f"{float(rmse):.4f}" if rmse is not None else "—"
    print(
        f"  MC trial {completed}/{total}  id={trial_id}  success={ok}  rmse_pos={rmse_s} m",
        flush=True,
    )


def run_monte_carlo(
    *,
    nominal_vehicle: VehicleParams,
    base_seed: int,
    n_trials: int,
    trial_fn: Callable[[int, VehicleParams, dict[str, float]], dict[str, Any]],
    spec: PerturbationSpec | None = None,
    redesign_controller: bool = False,
    trial_ids: range | list[int] | None = None,
    progress: ProgressFn | bool | None = None,
) -> MonteCarloResult:
    """
    Run MC trials.

    ``trial_fn(trial_id, plant_vehicle, param_dict) -> metrics row`` must be
    deterministic given those inputs (and fixed controller/reference outside).

    ``progress``: ``True`` → single-line progress bar for this id list;
    callable for custom hooks; ``None``/``False`` → silent (tests).
    """
    if n_trials < 1:
        msg = "n_trials must be >= 1"
        raise ValueError(msg)

    ids = list(trial_ids) if trial_ids is not None else list(range(n_trials))
    total = len(ids)

    if progress is True:
        progress_fn: ProgressFn | None = McProgressBar(total)
    elif callable(progress):
        progress_fn = progress
    else:
        progress_fn = None

    trials: list[dict[str, Any]] = []
    for i, trial_id in enumerate(ids, start=1):
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
        if progress_fn is not None:
            progress_fn(i, total, int(trial_id), row)

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
