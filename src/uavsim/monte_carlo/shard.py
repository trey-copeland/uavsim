"""Trial index partitioning and shard merge for Monte Carlo."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from uavsim.monte_carlo.io import read_trials_csv, write_trials_csv, write_trials_json
from uavsim.monte_carlo.summary import summarize_trials
from uavsim.results import write_json, write_yaml


@dataclass(frozen=True)
class ShardPlan:
    """Disjoint partition of trial indices 0..n_trials-1 across shards."""

    n_trials: int
    n_shards: int
    ranges: tuple[tuple[int, int], ...]  # (start, end) half-open per shard

    def trial_ids(self, shard_id: int) -> list[int]:
        if shard_id < 0 or shard_id >= self.n_shards:
            msg = f"shard_id {shard_id} out of range for n_shards={self.n_shards}"
            raise ValueError(msg)
        start, end = self.ranges[shard_id]
        return list(range(start, end))

    def to_dict(self) -> dict[str, Any]:
        return {
            "n_trials": self.n_trials,
            "n_shards": self.n_shards,
            "ranges": [
                {"shard_id": i, "start": s, "end": e}
                for i, (s, e) in enumerate(self.ranges)
            ],
        }


def partition_trials(n_trials: int, n_shards: int) -> ShardPlan:
    """
    Partition ``0..n_trials-1`` into ``n_shards`` contiguous, nearly equal ranges.

    Empty shards are allowed when n_shards > n_trials (later shards get []).
    """
    if n_trials < 1:
        msg = "n_trials must be >= 1"
        raise ValueError(msg)
    if n_shards < 1:
        msg = "n_shards must be >= 1"
        raise ValueError(msg)

    base, rem = divmod(n_trials, n_shards)
    ranges: list[tuple[int, int]] = []
    cursor = 0
    for i in range(n_shards):
        size = base + (1 if i < rem else 0)
        ranges.append((cursor, cursor + size))
        cursor += size
    assert cursor == n_trials
    return ShardPlan(n_trials=n_trials, n_shards=n_shards, ranges=tuple(ranges))


def merge_trial_rows(shard_trial_lists: list[list[dict[str, Any]]]) -> list[dict[str, Any]]:
    """Merge trial rows from shards; sort by trial_id; reject duplicate ids."""
    merged: list[dict[str, Any]] = []
    seen: set[int] = set()
    for rows in shard_trial_lists:
        for row in rows:
            tid = int(row["trial_id"])
            if tid in seen:
                msg = f"Duplicate trial_id {tid} across shards"
                raise ValueError(msg)
            seen.add(tid)
            merged.append(row)
    merged.sort(key=lambda r: int(r["trial_id"]))
    return merged


def merge_shard_directories(
    shard_dirs: list[Path],
    *,
    expected_n_trials: int | None = None,
    redesign_controller: bool = False,
    base_seed: int | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """
    Load ``trials.csv`` from each shard dir, merge, and compute summary.

    Missing shard or missing trials.csv → raises (fail the study).
    """
    if not shard_dirs:
        msg = "No shard directories to merge"
        raise ValueError(msg)

    lists: list[list[dict[str, Any]]] = []
    for d in shard_dirs:
        d = Path(d)
        csv_path = d / "trials.csv"
        if not csv_path.is_file():
            msg = f"Missing trials.csv in shard dir: {d}"
            raise FileNotFoundError(msg)
        lists.append(read_trials_csv(csv_path))

    trials = merge_trial_rows(lists)
    if expected_n_trials is not None and len(trials) != expected_n_trials:
        msg = (
            f"Merged trial count {len(trials)} != expected n_trials {expected_n_trials} "
            f"(shard failure or incomplete coverage)"
        )
        raise ValueError(msg)

    summary = summarize_trials(trials)
    summary["redesign_controller"] = redesign_controller
    if base_seed is not None:
        summary["base_seed"] = int(base_seed)
    summary["merged_from_shards"] = len(shard_dirs)
    return trials, summary


def write_shard_artifacts(
    shard_dir: Path,
    *,
    shard_id: int,
    n_shards: int,
    trials: list[dict[str, Any]],
    plan: ShardPlan | None = None,
    extra_meta: dict[str, Any] | None = None,
) -> Path:
    """Write a single shard's trials + metadata under ``shard_dir``."""
    shard_dir = Path(shard_dir)
    shard_dir.mkdir(parents=True, exist_ok=True)
    write_trials_csv(shard_dir / "trials.csv", trials)
    write_trials_json(shard_dir / "trials.json", trials)
    meta: dict[str, Any] = {
        "schema_version": 1,
        "shard_id": shard_id,
        "n_shards": n_shards,
        "n_trials_in_shard": len(trials),
        "trial_ids": [int(t["trial_id"]) for t in trials],
        "status": "success",
    }
    if plan is not None:
        meta["plan"] = plan.to_dict()
    if extra_meta:
        meta.update(extra_meta)
    write_json(shard_dir / "shard_meta.json", meta)
    return shard_dir


def write_merged_mc_artifacts(
    mc_dir: Path,
    trials: list[dict[str, Any]],
    summary: dict[str, Any],
    *,
    plan: ShardPlan | None = None,
) -> None:
    mc_dir = Path(mc_dir)
    mc_dir.mkdir(parents=True, exist_ok=True)
    write_trials_csv(mc_dir / "trials.csv", trials)
    write_trials_json(mc_dir / "trials.json", trials)
    write_json(mc_dir / "summary.json", summary)
    if plan is not None:
        write_yaml(mc_dir / "shard_plan.yaml", plan.to_dict())


def summaries_close(
    a: dict[str, Any],
    b: dict[str, Any],
    *,
    rtol: float = 1e-9,
    atol: float = 1e-12,
) -> tuple[bool, str]:
    """Soft compare two MC summaries (mean metrics); returns (ok, message)."""
    if a.get("n_trials") != b.get("n_trials"):
        return False, f"n_trials differ: {a.get('n_trials')} vs {b.get('n_trials')}"
    if a.get("n_success") != b.get("n_success"):
        return False, f"n_success differ: {a.get('n_success')} vs {b.get('n_success')}"

    ma = a.get("metrics") or {}
    mb = b.get("metrics") or {}
    keys = set(ma) | set(mb)
    for k in sorted(keys):
        if k not in ma or k not in mb:
            return False, f"metric key missing: {k}"
        va, vb = ma[k].get("mean"), mb[k].get("mean")
        if va is None or vb is None:
            continue
        if abs(float(va) - float(vb)) > atol + rtol * max(abs(float(va)), abs(float(vb))):
            return False, f"metric {k} mean differ: {va} vs {vb}"
    return True, "ok"
