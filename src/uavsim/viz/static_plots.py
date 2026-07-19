"""Static matplotlib figure pack (V3–V6, V8)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from uavsim.viz.loaders import (
    RunArtifacts,
    body_axes_ned,
    interpolate_ref_at,
    ned_to_plot,
    saturation_mask,
)
from uavsim.viz.mc_plots import write_mc_figures


def write_static_figures(art: RunArtifacts, fig_dir: Path | None = None) -> list[Path]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig_dir = fig_dir or (art.run_dir / "figures")
    fig_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    if art.t is not None and art.x is not None and art.u is not None:
        written.extend(_timeseries_with_saturation(art, fig_dir, plt))
        written.extend(_error_strips(art, fig_dir, plt))
        still = _flight_still(art, fig_dir, plt)
        if still is not None:
            written.append(still)
        path3d = _path_3d(art, fig_dir, plt)
        if path3d is not None:
            written.append(path3d)

    written.extend(write_mc_figures(art, fig_dir))
    return written


def _timeseries_with_saturation(art: RunArtifacts, fig_dir: Path, plt: Any) -> list[Path]:
    t, x, u = art.t, art.x, art.u
    assert t is not None and x is not None and u is not None
    sat = saturation_mask(u, art.limits)

    fig, axes = plt.subplots(3, 1, figsize=(8, 7.5), sharex=True)
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

    axes[2].plot(t, u[:, 0], label="F", color="C0")
    axes[2].plot(t, u[:, 1], label="τφ", color="C1")
    axes[2].plot(t, u[:, 2], label="τθ", color="C2")
    axes[2].plot(t, u[:, 3], label="τψ", color="C3")
    # Limit lines
    if np.isfinite(art.limits.thrust_max_n):
        axes[2].axhline(
            art.limits.thrust_max_n, color="C0", ls="--", lw=0.8, alpha=0.7, label="F_max"
        )
    if np.isfinite(art.limits.torque_max_nm):
        axes[2].axhline(art.limits.torque_max_nm, color="gray", ls="--", lw=0.8, alpha=0.6)
        axes[2].axhline(-art.limits.torque_max_nm, color="gray", ls="--", lw=0.8, alpha=0.6)
    # Saturation shading (V4)
    if np.any(sat):
        ymin, ymax = axes[2].get_ylim()
        axes[2].fill_between(t, ymin, ymax, where=sat, color="red", alpha=0.15, label="near limit")
    axes[2].set_ylabel("u")
    axes[2].set_xlabel("t [s]")
    axes[2].legend(loc="best", fontsize=7)
    axes[2].grid(True, alpha=0.3)
    fig.suptitle(f"Nominal timeseries — {art.study_id}")
    fig.tight_layout()
    out = fig_dir / "nominal_timeseries.png"
    fig.savefig(out, dpi=120)
    plt.close(fig)
    return [out]


def _error_strips(art: RunArtifacts, fig_dir: Path, plt: Any) -> list[Path]:
    """V3: position error and control effort strips."""
    t, x, u = art.t, art.x, art.u
    assert t is not None and x is not None and u is not None

    if art.t_ref is not None and art.x_ref is not None:
        e = np.zeros((t.size, 3))
        for i, ti in enumerate(t):
            xref = interpolate_ref_at(art.t_ref, art.x_ref, float(ti))
            e[i] = x[i, 0:3] - xref[0:3]
    else:
        e = x[:, 0:3] - x[0:1, 0:3]  # vs initial (weak); prefer hold at 0
        if art.metrics:
            # hold ref often zero; use zero when hold
            e = x[:, 0:3].copy()

    fig, axes = plt.subplots(2, 1, figsize=(8, 5), sharex=True)
    axes[0].plot(t, e[:, 0], label="e_N")
    axes[0].plot(t, e[:, 1], label="e_E")
    axes[0].plot(t, e[:, 2], label="e_D")
    axes[0].plot(t, np.linalg.norm(e, axis=1), "k--", lw=1, label="|e|")
    axes[0].set_ylabel("pos error [m]")
    axes[0].legend(loc="best", fontsize=8)
    axes[0].grid(True, alpha=0.3)

    axes[1].plot(t, u[:, 0], label="F")
    axes[1].plot(t, np.linalg.norm(u[:, 1:4], axis=1), label="|τ|")
    sat = saturation_mask(u, art.limits)
    if np.any(sat):
        axes[1].scatter(t[sat], u[sat, 0], c="red", s=8, zorder=5, label="sat")
    axes[1].set_ylabel("control")
    axes[1].set_xlabel("t [s]")
    axes[1].legend(loc="best", fontsize=8)
    axes[1].grid(True, alpha=0.3)
    fig.suptitle("Tracking error + control (V3/V4)")
    fig.tight_layout()
    out = fig_dir / "error_control_strips.png"
    fig.savefig(out, dpi=120)
    plt.close(fig)
    return [out]


def _path_3d(art: RunArtifacts, fig_dir: Path, plt: Any) -> Path | None:
    if art.x is None:
        return None
    plot = ned_to_plot(art.x[:, 0:3])
    fig = plt.figure(figsize=(6, 5))
    ax = fig.add_subplot(111, projection="3d")
    ax.plot(plot[:, 0], plot[:, 1], plot[:, 2], label="flown", color="C0")
    if art.x_ref is not None:
        pref = ned_to_plot(art.x_ref[:, 0:3])
        ax.plot(pref[:, 0], pref[:, 1], pref[:, 2], "--", label="ref", color="C1", alpha=0.8)
    ax.scatter(plot[0, 0], plot[0, 1], plot[0, 2], c="green", s=30, label="start")
    ax.scatter(plot[-1, 0], plot[-1, 1], plot[-1, 2], c="red", s=30, label="end")
    ax.set_xlabel("N [m]")
    ax.set_ylabel("E [m]")
    ax.set_zlabel("up [m]")
    ax.legend(fontsize=7)
    ax.set_title(f"Path 3D — {art.study_id}")
    out = fig_dir / "nominal_path_3d.png"
    fig.savefig(out, dpi=120)
    plt.close(fig)
    return out


def _flight_still(art: RunArtifacts, fig_dir: Path, plt: Any) -> Path | None:
    """V8: single keyframe mid-flight with body axes."""
    if art.t is None or art.x is None:
        return None
    mid = art.t.size // 2
    p = ned_to_plot(art.x[mid, 0:3])
    r = body_axes_ned(art.x[mid, 3:6])
    # body axes in plot frame (flip z component of vectors for up)
    scale = 0.35 * max(0.5, float(np.ptp(art.x[:, 0:3], axis=0).max()))

    fig = plt.figure(figsize=(6, 5))
    ax = fig.add_subplot(111, projection="3d")
    path = ned_to_plot(art.x[:, 0:3])
    ax.plot(path[:, 0], path[:, 1], path[:, 2], color="C0", alpha=0.5, lw=1)
    if art.x_ref is not None:
        pref = ned_to_plot(art.x_ref[:, 0:3])
        ax.plot(pref[:, 0], pref[:, 1], pref[:, 2], "--", color="C1", alpha=0.6, lw=1)
    ax.scatter([p[0]], [p[1]], [p[2]], c="k", s=40, zorder=5)
    colors = ["r", "g", "b"]
    labels = ["body-x", "body-y", "body-z"]
    for i in range(3):
        v = r[:, i].copy()
        v_plot = np.array([v[0], v[1], -v[2]]) * scale
        ax.quiver(
            p[0],
            p[1],
            p[2],
            v_plot[0],
            v_plot[1],
            v_plot[2],
            color=colors[i],
            arrow_length_ratio=0.2,
            label=labels[i],
        )
    ax.set_xlabel("N [m]")
    ax.set_ylabel("E [m]")
    ax.set_zlabel("up [m]")
    ax.set_title(f"Flight still t={art.t[mid]:.2f}s (V8)")
    ax.legend(fontsize=7)
    out = fig_dir / "flight_still.png"
    fig.savefig(out, dpi=140)
    plt.close(fig)
    return out
