"""Unit tests: trial partition and shard merge."""

from __future__ import annotations

from pathlib import Path

import pytest

from uavsim.monte_carlo import (
    merge_shard_directories,
    merge_trial_rows,
    partition_trials,
    write_shard_artifacts,
)


def test_partition_covers_all_trials() -> None:
    plan = partition_trials(10, 3)
    ids = [i for s in range(3) for i in plan.trial_ids(s)]
    assert ids == list(range(10))
    assert plan.ranges[0] == (0, 4)
    assert plan.ranges[1] == (4, 7)
    assert plan.ranges[2] == (7, 10)


def test_partition_more_shards_than_trials() -> None:
    plan = partition_trials(2, 4)
    assert plan.trial_ids(0) == [0]
    assert plan.trial_ids(1) == [1]
    assert plan.trial_ids(2) == []
    assert plan.trial_ids(3) == []


def test_merge_rejects_duplicates() -> None:
    with pytest.raises(ValueError, match="Duplicate"):
        merge_trial_rows(
            [
                [{"trial_id": 0, "rmse_position_m": 0.1}],
                [{"trial_id": 0, "rmse_position_m": 0.2}],
            ]
        )


def test_merge_shard_directories(tmp_path: Path) -> None:
    plan = partition_trials(4, 2)
    d0 = write_shard_artifacts(
        tmp_path / "s0",
        shard_id=0,
        n_shards=2,
        trials=[
            {"trial_id": 0, "rmse_position_m": 0.1, "success": True, "sim_success": True},
            {"trial_id": 1, "rmse_position_m": 0.2, "success": True, "sim_success": True},
        ],
        plan=plan,
    )
    d1 = write_shard_artifacts(
        tmp_path / "s1",
        shard_id=1,
        n_shards=2,
        trials=[
            {"trial_id": 2, "rmse_position_m": 0.3, "success": False, "sim_success": True},
            {"trial_id": 3, "rmse_position_m": 0.4, "success": True, "sim_success": True},
        ],
        plan=plan,
    )
    trials, summary = merge_shard_directories(
        [d0, d1], expected_n_trials=4, base_seed=7
    )
    assert [t["trial_id"] for t in trials] == [0, 1, 2, 3]
    assert summary["n_trials"] == 4
    assert summary["n_success"] == 3
    assert summary["base_seed"] == 7
