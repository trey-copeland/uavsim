"""Compare two run directories (metrics + overlays) — pure artifact consumer."""

from __future__ import annotations

import contextlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import yaml


@dataclass
class CompareResult:
    output_dir: Path
    summary_md: Path
    delta_json: Path
    figures: list[Path] = field(default_factory=list)
    deltas: dict[str, Any] = field(default_factory=dict)
    interactive: Path | None = None


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


def _run_label(run_dir: Path, manifest: dict[str, Any] | None) -> str:
    if manifest and manifest.get("study_id"):
        return str(manifest["study_id"])
    return run_dir.name


METRIC_KEYS = (
    "rmse_position_m",
    "max_position_error_m",
    "final_position_error_m",
    "time_in_bounds_frac",
    "rmse_attitude_rad",
    "max_attitude_error_rad",
    "rmse_velocity_m_s",
    "control_effort_proxy",
    "peak_thrust_n",
    "peak_torque_nm",
    "success",
    "sim_success",
)


def compute_metric_deltas(
    metrics_a: dict[str, Any],
    metrics_b: dict[str, Any],
) -> dict[str, Any]:
    """b - a for numeric metrics; boolean pair for flags."""
    rows: list[dict[str, Any]] = []
    for key in METRIC_KEYS:
        if key not in metrics_a and key not in metrics_b:
            continue
        va, vb = metrics_a.get(key), metrics_b.get(key)
        if isinstance(va, bool) or isinstance(vb, bool):
            rows.append({"metric": key, "a": va, "b": vb, "delta": None})
            continue
        try:
            fa, fb = float(va), float(vb)
            rows.append({"metric": key, "a": fa, "b": fb, "delta": fb - fa})
        except (TypeError, ValueError):
            rows.append({"metric": key, "a": va, "b": vb, "delta": None})
    return {"schema_version": 1, "rows": rows}


def compare_runs(
    run_a: str | Path,
    run_b: str | Path,
    *,
    output_dir: str | Path | None = None,
    figures: bool = True,
    interactive: bool = False,
) -> CompareResult:
    """
    Compare two run directories.

    Alignment: prefer identical time grids; otherwise resample B onto A's time
    base with linear interpolation (documented soft policy for SIL↔SIL).
    """
    run_a = Path(run_a)
    run_b = Path(run_b)
    if not run_a.is_dir() or not run_b.is_dir():
        msg = f"Both run directories must exist: {run_a}, {run_b}"
        raise FileNotFoundError(msg)

    metrics_a = _load_json(run_a / "nominal" / "metrics.json") or {}
    metrics_b = _load_json(run_b / "nominal" / "metrics.json") or {}
    man_a = _load_yaml(run_a / "manifest.yaml")
    man_b = _load_yaml(run_b / "manifest.yaml")
    label_a = _run_label(run_a, man_a)
    label_b = _run_label(run_b, man_b)

    deltas = compute_metric_deltas(metrics_a, metrics_b)
    deltas["run_a"] = {
        "path": str(run_a),
        "label": label_a,
        "execution": (man_a or {}).get("execution"),
        "seed": (man_a or {}).get("seed"),
    }
    deltas["run_b"] = {
        "path": str(run_b),
        "label": label_b,
        "execution": (man_b or {}).get("execution"),
        "seed": (man_b or {}).get("seed"),
    }

    if output_dir is None:
        out = Path("runs") / f"compare_{label_a}_vs_{label_b}"
    else:
        out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "figures").mkdir(exist_ok=True)

    delta_path = out / "metric_deltas.json"
    with delta_path.open("w", encoding="utf-8") as f:
        json.dump(deltas, f, indent=2, sort_keys=True)
        f.write("\n")

    lines = [
        f"# Compare: {label_a} vs {label_b}",
        "",
        f"- **A**: `{run_a}`",
        f"- **B**: `{run_b}`",
        "",
        "## Metric deltas (B − A)",
        "",
        "| metric | A | B | delta |",
        "|--------|---|---|-------|",
    ]
    for row in deltas["rows"]:
        d = row["delta"]
        d_s = f"{d:.6g}" if isinstance(d, float) else str(d)
        lines.append(f"| {row['metric']} | {row['a']} | {row['b']} | {d_s} |")
    lines.append("")
    summary_md = out / "compare_summary.md"
    summary_md.write_text("\n".join(lines), encoding="utf-8")

    fig_paths: list[Path] = []
    if figures:
        with contextlib.suppress(ImportError):
            fig_paths = _overlay_figures(run_a, run_b, out / "figures", label_a, label_b)

    interactive_path: Path | None = None
    if interactive:
        try:
            from uavsim.viz.flight3d import write_compare_flight_html
            from uavsim.viz.loaders import load_run

            interactive_path = write_compare_flight_html(
                load_run(run_a),
                load_run(run_b),
                out / "figures" / "compare_3d.html",
            )
            fig_paths.append(interactive_path)
        except (ImportError, FileNotFoundError):
            pass

    return CompareResult(
        output_dir=out,
        summary_md=summary_md,
        delta_json=delta_path,
        figures=fig_paths,
        deltas=deltas,
        interactive=interactive_path,
    )


def _load_ts(run_dir: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray] | None:
    path = run_dir / "nominal" / "timeseries.npz"
    if not path.is_file():
        return None
    data = np.load(path)
    return data["t"], data["x"], data["u"]


def _resample_x(t_src: np.ndarray, x_src: np.ndarray, t_dst: np.ndarray) -> np.ndarray:
    out = np.zeros((t_dst.size, x_src.shape[1]), dtype=float)
    for j in range(x_src.shape[1]):
        out[:, j] = np.interp(t_dst, t_src, x_src[:, j])
    return out


def _overlay_figures(
    run_a: Path,
    run_b: Path,
    fig_dir: Path,
    label_a: str,
    label_b: str,
) -> list[Path]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    ts_a = _load_ts(run_a)
    ts_b = _load_ts(run_b)
    if ts_a is None or ts_b is None:
        return []

    t_a, x_a, _u_a = ts_a
    t_b, x_b, _u_b = ts_b
    # Align B onto A's time base when grids differ
    if t_a.shape != t_b.shape or not np.allclose(t_a, t_b, rtol=0, atol=1e-9):
        x_b_aligned = _resample_x(t_b, x_b, t_a)
        t = t_a
        x_b_use = x_b_aligned
    else:
        t = t_a
        x_b_use = x_b

    written: list[Path] = []

    fig, axes = plt.subplots(3, 1, figsize=(8, 7), sharex=True)
    for i, name in enumerate(["N", "E", "D"]):
        axes[i].plot(t, x_a[:, i], label=f"{label_a}", linewidth=1.5)
        axes[i].plot(t, x_b_use[:, i], "--", label=f"{label_b}", linewidth=1.2)
        axes[i].set_ylabel(f"{name} [m]")
        axes[i].grid(True, alpha=0.3)
        axes[i].legend(loc="best", fontsize=8)
    axes[-1].set_xlabel("t [s]")
    fig.suptitle("Position overlay (NED)")
    fig.tight_layout()
    out = fig_dir / "position_overlay.png"
    fig.savefig(out, dpi=120)
    plt.close(fig)
    written.append(out)

    fig = plt.figure(figsize=(6, 5))
    ax = fig.add_subplot(111, projection="3d")
    ax.plot(x_a[:, 0], x_a[:, 1], -x_a[:, 2], label=label_a)
    ax.plot(x_b_use[:, 0], x_b_use[:, 1], -x_b_use[:, 2], "--", label=label_b)
    ax.set_xlabel("N [m]")
    ax.set_ylabel("E [m]")
    ax.set_zlabel("up [m]")
    ax.legend(fontsize=8)
    ax.set_title("Path overlay (up = −D)")
    out = fig_dir / "path_overlay_3d.png"
    fig.savefig(out, dpi=120)
    plt.close(fig)
    written.append(out)

    return written
