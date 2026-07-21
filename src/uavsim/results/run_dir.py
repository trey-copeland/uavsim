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


def write_nominal_timeseries(
    run_dir: Path,
    t: np.ndarray,
    x: np.ndarray,
    u: np.ndarray,
    *,
    x_hat: np.ndarray | None = None,
) -> Path:
    """Write nominal timeseries. Optional ``x_hat`` is the observer estimate."""
    path = run_dir / "nominal" / "timeseries.npz"
    payload: dict[str, Any] = {"t": t, "x": x, "u": u}
    if x_hat is not None:
        payload["x_hat"] = np.asarray(x_hat, dtype=float)
    np.savez_compressed(path, **payload)
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


def write_text_report(
    run_dir: Path,
    metrics: dict[str, Any],
    study_id: str,
    *,
    mc_summary: dict[str, Any] | None = None,
    feasibility: dict[str, Any] | None = None,
) -> Path:
    lines = [
        f"# Study report: {study_id}",
        "",
        "## Nominal metrics",
        "",
    ]
    for key, val in metrics.items():
        lines.append(f"- **{key}**: {val}")
    lines.append("")

    # V6: feasibility callouts
    if feasibility is not None:
        lines.extend(
            [
                "## Feasibility",
                "",
                f"- **ok**: {feasibility.get('ok')}",
                "",
            ]
        )
        issues = feasibility.get("issues") or []
        if issues:
            lines.append("### Issues")
            lines.append("")
            for issue in issues:
                if isinstance(issue, dict):
                    sev = issue.get("severity", "?")
                    code = issue.get("code", "?")
                    msg = issue.get("message", "")
                    lines.append(f"- **[{sev}] {code}**: {msg}")
                else:
                    lines.append(f"- {issue}")
            lines.append("")
        summary = feasibility.get("summary") or {}
        if summary:
            lines.append("### Summary stats")
            lines.append("")
            for k, v in summary.items():
                lines.append(f"- **{k}**: {v}")
            lines.append("")

    if mc_summary is not None:
        lines.extend(
            [
                "## Monte Carlo summary",
                "",
                f"- **n_trials**: {mc_summary.get('n_trials')}",
                f"- **n_success**: {mc_summary.get('n_success')}",
                f"- **failure_rate**: {mc_summary.get('failure_rate')}",
                f"- **base_seed**: {mc_summary.get('base_seed')}",
                f"- **redesign_controller**: {mc_summary.get('redesign_controller')}",
                "",
            ]
        )
        metric_stats = mc_summary.get("metrics") or {}
        if metric_stats:
            lines.append("### Metric statistics")
            lines.append("")
            for name, stats in metric_stats.items():
                if not isinstance(stats, dict):
                    continue
                lines.append(
                    f"- **{name}**: mean={stats.get('mean'):.6g}  "
                    f"std={stats.get('std'):.6g}  "
                    f"p50={stats.get('p50'):.6g}  "
                    f"p95={stats.get('p95'):.6g}"
                )
            lines.append("")
        corrs = mc_summary.get("correlations_vs_rmse_position") or {}
        if corrs:
            lines.append("### Correlations vs RMSE position")
            lines.append("")
            for pname, cval in corrs.items():
                lines.append(f"- **{pname}**: {cval}")
            lines.append("")

    path = run_dir / "reports" / "summary.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
