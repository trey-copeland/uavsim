"""Monte Carlo engine, sharding, merge, and docker orchestration hooks."""

from uavsim.monte_carlo.docker_run import default_image_name, docker_available, docker_study
from uavsim.monte_carlo.engine import MonteCarloResult, default_mc_progress, run_monte_carlo
from uavsim.monte_carlo.io import read_trials_csv, write_trials_csv, write_trials_json
from uavsim.monte_carlo.perturb import PerturbationSpec, perturb_vehicle, trial_rng
from uavsim.monte_carlo.shard import (
    ShardPlan,
    merge_shard_directories,
    merge_trial_rows,
    partition_trials,
    summaries_close,
    write_merged_mc_artifacts,
    write_shard_artifacts,
)
from uavsim.monte_carlo.summary import summarize_trials

__all__ = [
    "MonteCarloResult",
    "PerturbationSpec",
    "ShardPlan",
    "default_image_name",
    "default_mc_progress",
    "docker_available",
    "docker_study",
    "merge_shard_directories",
    "merge_trial_rows",
    "partition_trials",
    "perturb_vehicle",
    "read_trials_csv",
    "run_monte_carlo",
    "summaries_close",
    "summarize_trials",
    "trial_rng",
    "write_merged_mc_artifacts",
    "write_shard_artifacts",
    "write_trials_csv",
    "write_trials_json",
]
