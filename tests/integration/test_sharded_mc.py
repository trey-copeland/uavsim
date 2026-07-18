"""Integration: sharded MC matches unsharded; docker optional smoke."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from uavsim.monte_carlo import docker_available, read_trials_csv, summaries_close
from uavsim.studies import run_study

ROOT = Path(__file__).resolve().parents[2]
SMOKE = ROOT / "configs" / "studies" / "hover_mc_smoke.yaml"


@pytest.fixture
def runs_tmp(tmp_path: Path) -> Path:
    return tmp_path / "runs"


def test_sharded_matches_unsharded(runs_tmp: Path) -> None:
    single = run_study(
        SMOKE,
        output_root=runs_tmp / "single",
        n_trials_override=4,
        n_shards=1,
        backend="local",
    )
    multi = run_study(
        SMOKE,
        output_root=runs_tmp / "multi",
        n_trials_override=4,
        n_shards=2,
        backend="local",
    )
    assert single.mc_summary is not None
    assert multi.mc_summary is not None
    ok, msg = summaries_close(single.mc_summary, multi.mc_summary)
    assert ok, msg

    t1 = read_trials_csv(single.run_dir / "monte_carlo" / "trials.csv")
    t2 = read_trials_csv(multi.run_dir / "monte_carlo" / "trials.csv")
    assert len(t1) == len(t2) == 4
    for a, b in zip(t1, t2, strict=True):
        assert a["trial_id"] == b["trial_id"]
        assert a["mass_kg"] == b["mass_kg"]
        assert a["rmse_position_m"] == pytest.approx(b["rmse_position_m"], rel=0, abs=1e-12)

    # Intermediate shards written
    shards = list((multi.run_dir / "monte_carlo" / "shards").glob("shard_*"))
    assert len(shards) == 2


def test_mc_shard_and_merge_cli(runs_tmp: Path, tmp_path: Path) -> None:
    from uavsim.cli.main import main

    s0 = tmp_path / "shard0"
    s1 = tmp_path / "shard1"
    code = main(
        [
            "mc-shard",
            str(SMOKE),
            "--shard-id",
            "0",
            "--shards",
            "2",
            "--output",
            str(s0),
            "--n-trials",
            "4",
        ]
    )
    assert code == 0
    code = main(
        [
            "mc-shard",
            str(SMOKE),
            "--shard-id",
            "1",
            "--shards",
            "2",
            "--output",
            str(s1),
            "--n-trials",
            "4",
        ]
    )
    assert code == 0
    merged = tmp_path / "merged"
    code = main(
        [
            "mc-merge",
            str(s0),
            str(s1),
            "--output",
            str(merged),
            "--n-trials",
            "4",
            "--seed",
            "7",
        ]
    )
    assert code == 0
    summary = json.loads((merged / "summary.json").read_text(encoding="utf-8"))
    assert summary["n_trials"] == 4


@pytest.mark.skipif(not docker_available(), reason="docker not available")
def test_docker_study_smoke(runs_tmp: Path) -> None:
    """Optional: full study inside container (builds image if needed)."""
    result = run_study(
        SMOKE,
        output_root=runs_tmp,
        n_trials_override=2,
        backend="docker",
        n_shards=1,
        repo_root=ROOT,
    )
    assert result.backend == "docker"
    assert result.mc_summary is not None
    assert result.mc_summary["n_trials"] == 2
    assert (result.run_dir / "monte_carlo" / "trials.csv").is_file()
