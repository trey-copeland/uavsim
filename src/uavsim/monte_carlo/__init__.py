"""Monte Carlo engine, sharding hooks, and merge."""

from uavsim.monte_carlo.engine import MonteCarloResult, run_monte_carlo
from uavsim.monte_carlo.io import read_trials_csv, write_trials_csv, write_trials_json
from uavsim.monte_carlo.perturb import PerturbationSpec, perturb_vehicle, trial_rng
from uavsim.monte_carlo.summary import summarize_trials

__all__ = [
    "MonteCarloResult",
    "PerturbationSpec",
    "perturb_vehicle",
    "read_trials_csv",
    "run_monte_carlo",
    "summarize_trials",
    "trial_rng",
    "write_trials_csv",
    "write_trials_json",
]
