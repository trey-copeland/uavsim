"""Report / figure generation as a pure consumer of run directories."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from uavsim.monte_carlo.io import read_trials_csv
from uavsim.results import write_text_report


@dataclass
class ReportResult:
    run_dir: Path
    summary_md: Path
    figures: list[Path]
    message: str


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, dict) else None


def _load_yaml(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else None


def generate_report(
    run_dir: str | Path,
    *,
    figures: bool = True,
) -> ReportResult:
    """
    Rebuild ``reports/summary.md`` from artifacts; optionally write figures.

    Does not re-run simulation. Figures require matplotlib (optional).
    """
    run_dir = Path(run_dir)
    if not run_dir.is_dir():
        msg = f"Run directory not found: {run_dir}"
        raise FileNotFoundError(msg)

    metrics = _load_json(run_dir / "nominal" / "metrics.json") or {}
    mc_summary = _load_json(run_dir / "monte_carlo" / "summary.json")
    study_id = run_dir.name
    manifest = _load_yaml(run_dir / "manifest.yaml")
    if manifest and "study_id" in manifest:
        study_id = str(manifest["study_id"])

    (run_dir / "reports").mkdir(exist_ok=True)
    summary_md = write_text_report(run_dir, metrics, study_id, mc_summary=mc_summary)

    fig_paths: list[Path] = []
    msg = "report written"
    if figures:
        try:
            fig_paths = _write_figures(run_dir, mc_summary)
            if fig_paths:
                msg = f"report + {len(fig_paths)} figure(s)"
            else:
                msg = "report written (no figure data available)"
        except ImportError:
            msg = "report written (matplotlib not installed; skip figures)"

    return ReportResult(
        run_dir=run_dir,
        summary_md=summary_md,
        figures=fig_paths,
        message=msg,
    )


def _write_figures(
    run_dir: Path,
    mc_summary: dict[str, Any] | None,
) -> list[Path]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig_dir = run_dir / "figures"
    fig_dir.mkdir(exist_ok=True)
    written: list[Path] = []

    # Nominal tracking timeseries
    ts_path = run_dir / "nominal" / "timeseries.npz"
    if ts_path.is_file():
        data = np.load(ts_path)
        t = data["t"]
        x = data["x"]
        u = data["u"]

        fig, axes = plt.subplots(3, 1, figsize=(8, 7), sharex=True)
        axes[0].plot(t, x[:, 0], label="N")
        axes[0].plot(t, x[:, 1], label="E")
        axes[0].plot(t, x[:, 2], label="D")
        axes[0].set_ylabel("pos [m]")
        axes[0].legend(loc="best", fontsize=8)
        axes[0].grid(True, alpha=0.3)

        axes[1].plot(t, np.rad2deg(x[:, 3]), label="φ")
        axes[1].plot(t, np.rad2deg(x[:, 4]), label="θ")
        axes[1].plot(t, np.rad2deg(x[:, 5]), label="ψ")
        axes[1].set_ylabel("euler [deg]")
        axes[1].legend(loc="best", fontsize=8)
        axes[1].grid(True, alpha=0.3)

        axes[2].plot(t, u[:, 0], label="F")
        axes[2].plot(t, u[:, 1], label="τφ")
        axes[2].plot(t, u[:, 2], label="τθ")
        axes[2].plot(t, u[:, 3], label="τψ")
        axes[2].set_ylabel("u")
        axes[2].set_xlabel("t [s]")
        axes[2].legend(loc="best", fontsize=8)
        axes[2].grid(True, alpha=0.3)
        fig.suptitle("Nominal closed-loop timeseries")
        fig.tight_layout()
        out = fig_dir / "nominal_timeseries.png"
        fig.savefig(out, dpi=120)
        plt.close(fig)
        written.append(out)

        # 3D path (N, E, -D as up for readability)
        fig = plt.figure(figsize=(6, 5))
        ax = fig.add_subplot(111, projection="3d")
        ax.plot(x[:, 0], x[:, 1], -x[:, 2])
        ax.set_xlabel("N [m]")
        ax.set_ylabel("E [m]")
        ax.set_zlabel("up [m]")
        ax.set_title("Nominal path (NED → up=-D)")
        out = fig_dir / "nominal_path_3d.png"
        fig.savefig(out, dpi=120)
        plt.close(fig)
        written.append(out)

    # MC RMSE histogram
    trials_path = run_dir / "monte_carlo" / "trials.csv"
    if trials_path.is_file():
        trials = read_trials_csv(trials_path)
        rmse = [float(t["rmse_position_m"]) for t in trials if t.get("rmse_position_m") is not None]
        if rmse:
            fig, ax = plt.subplots(figsize=(6, 4))
            ax.hist(rmse, bins=min(20, max(5, len(rmse) // 2)), edgecolor="black", alpha=0.75)
            ax.set_xlabel("RMSE position [m]")
            ax.set_ylabel("count")
            title = "MC RMSE distribution"
            if mc_summary and mc_summary.get("n_trials"):
                title += f" (N={mc_summary['n_trials']})"
            ax.set_title(title)
            ax.grid(True, alpha=0.3)
            fig.tight_layout()
            out = fig_dir / "mc_rmse_hist.png"
            fig.savefig(out, dpi=120)
            plt.close(fig)
            written.append(out)

    return written
