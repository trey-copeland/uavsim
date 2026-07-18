"""Run directory I/O and manifests."""

from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from uavsim import __version__


def _git_identity() -> dict[str, Any]:
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        dirty = (
            subprocess.call(
                ["git", "diff", "--quiet"],
                stderr=subprocess.DEVNULL,
            )
            != 0
        )
        return {"git_commit": commit, "git_dirty": dirty}
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return {"git_commit": None, "git_dirty": None}


def create_run_directory(base: Path | str, study_id: str) -> Path:
    base = Path(base)
    base.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    run_dir = base / f"{study_id}_{stamp}"
    run_dir.mkdir(parents=False, exist_ok=False)
    (run_dir / "nominal").mkdir()
    (run_dir / "guidance").mkdir()
    (run_dir / "reference").mkdir()
    (run_dir / "reports").mkdir()
    return run_dir


def write_yaml(path: Path, data: Any) -> None:
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False)


def write_json(path: Path, data: Any) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write("\n")


def write_nominal_timeseries(run_dir: Path, t: np.ndarray, x: np.ndarray, u: np.ndarray) -> Path:
    path = run_dir / "nominal" / "timeseries.npz"
    np.savez_compressed(path, t=t, x=x, u=u)
    return path


def write_manifest(
    run_dir: Path,
    *,
    study_id: str,
    seed: int,
    config_hash: str,
    execution_mode: str = "sil",
    status: str = "success",
    extra: dict[str, Any] | None = None,
) -> Path:
    manifest: dict[str, Any] = {
        "schema_version": 1,
        "study_id": study_id,
        "created_at": datetime.now(UTC).isoformat(),
        "uavsim_version": __version__,
        "code_identity": _git_identity(),
        "config_hash": config_hash,
        "seed": seed,
        "execution": {"mode": execution_mode, "shards": 1},
        "status": status,
    }
    if extra:
        manifest.update(extra)
    path = run_dir / "manifest.yaml"
    write_yaml(path, manifest)
    return path


def write_text_report(run_dir: Path, metrics: dict[str, Any], study_id: str) -> Path:
    lines = [
        f"# Study report: {study_id}",
        "",
        "## Metrics",
        "",
    ]
    for key, val in metrics.items():
        lines.append(f"- **{key}**: {val}")
    lines.append("")
    path = run_dir / "reports" / "summary.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
