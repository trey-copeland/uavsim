"""Monte Carlo visualization pack (extended V5)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from uavsim.monte_carlo.summary import PARAM_KEYS
from uavsim.viz.loaders import RunArtifacts, ned_to_plot

# Compact set for multi-panel distributions / boxplots
DIST_METRICS = (
    "rmse_position_m",
    "max_position_error_m",
    "rmse_attitude_rad",
    "rmse_velocity_m_s",
    "control_effort_proxy",
    "peak_thrust_n",
    "peak_torque_nm",
    "time_in_bounds_frac",
)


def _col(trials: list[dict[str, Any]], key: str) -> np.ndarray | None:
    vals: list[float] = []
    for t in trials:
        v = t.get(key)
        if v is None:
            return None
        try:
            f = float(v)
        except (TypeError, ValueError):
            return None
        if not np.isfinite(f):
            return None
        vals.append(f)
    return np.asarray(vals, dtype=float) if vals else None


def write_mc_figures(art: RunArtifacts, fig_dir: Path | None = None) -> list[Path]:
    """Write full MC static pack when trials.csv is present."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    if not art.trials:
        return []
    fig_dir = fig_dir or (art.run_dir / "figures")
    fig_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    rmse = _col(art.trials, "rmse_position_m")
    if rmse is None:
        return []
    n = int(art.mc_summary.get("n_trials") if art.mc_summary else len(rmse))

    written.append(_hist_rmse(plt, fig_dir, rmse, n))
    written.append(_cdf_rmse(plt, fig_dir, rmse))
    written.extend(_param_scatters(plt, fig_dir, art.trials, rmse))
    written.extend(_metrics_boxplots(plt, fig_dir, art.trials))
    written.extend(_metrics_hist_grid(plt, fig_dir, art.trials))
    written.extend(_success_summary(plt, fig_dir, art.trials))
    written.extend(_correlation_bars(plt, fig_dir, art))
    written.extend(_exemplar_path_overlay(plt, fig_dir, art, rmse))

    return written


def _hist_rmse(plt: Any, fig_dir: Path, rmse: np.ndarray, n: int) -> Path:
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.hist(rmse, bins=min(20, max(5, len(rmse) // 2)), edgecolor="black", alpha=0.75)
    ax.set_xlabel("RMSE position [m]")
    ax.set_ylabel("count")
    ax.set_title(f"MC RMSE histogram (N={n})")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    out = fig_dir / "mc_rmse_hist.png"
    fig.savefig(out, dpi=120)
    plt.close(fig)
    return out


def _cdf_rmse(plt: Any, fig_dir: Path, rmse: np.ndarray) -> Path:
    s = np.sort(rmse)
    y = np.arange(1, s.size + 1) / s.size
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(s, y, drawstyle="steps-post")
    ax.set_xlabel("RMSE position [m]")
    ax.set_ylabel("CDF")
    ax.set_title("MC RMSE CDF")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    out = fig_dir / "mc_rmse_cdf.png"
    fig.savefig(out, dpi=120)
    plt.close(fig)
    return out


def _param_scatters(
    plt: Any, fig_dir: Path, trials: list[dict[str, Any]], rmse: np.ndarray
) -> list[Path]:
    """Scatter each perturbed param vs RMSE + multipanel summary."""
    written: list[Path] = []
    pairs: list[tuple[str, np.ndarray]] = []
    for key in PARAM_KEYS:
        col = _col(trials, key)
        if col is not None and col.size == rmse.size:
            pairs.append((key, col))
            fig, ax = plt.subplots(figsize=(5.5, 4))
            ax.scatter(col, rmse, alpha=0.75, edgecolors="k", linewidths=0.3)
            ax.set_xlabel(key)
            ax.set_ylabel("RMSE position [m]")
            ax.set_title(f"MC {key} vs RMSE")
            ax.grid(True, alpha=0.3)
            fig.tight_layout()
            # keep mass name for back-compat with existing tests
            name = "mc_mass_vs_rmse.png" if key == "mass_kg" else f"mc_{key}_vs_rmse.png"
            out = fig_dir / name
            fig.savefig(out, dpi=120)
            plt.close(fig)
            written.append(out)

    if len(pairs) >= 2:
        n = len(pairs)
        ncols = min(3, n)
        nrows = int(np.ceil(n / ncols))
        fig, axes = plt.subplots(nrows, ncols, figsize=(4 * ncols, 3.2 * nrows), squeeze=False)
        for i, (key, col) in enumerate(pairs):
            r, c = divmod(i, ncols)
            ax = axes[r][c]
            ax.scatter(col, rmse, alpha=0.7, s=18, edgecolors="k", linewidths=0.2)
            ax.set_xlabel(key, fontsize=8)
            ax.set_ylabel("RMSE [m]", fontsize=8)
            ax.grid(True, alpha=0.3)
        for j in range(len(pairs), nrows * ncols):
            r, c = divmod(j, ncols)
            axes[r][c].axis("off")
        fig.suptitle("MC parameter sensitivity vs RMSE")
        fig.tight_layout()
        out = fig_dir / "mc_param_scatters.png"
        fig.savefig(out, dpi=120)
        plt.close(fig)
        written.append(out)
    return written


def _metrics_boxplots(plt: Any, fig_dir: Path, trials: list[dict[str, Any]]) -> list[Path]:
    series: list[np.ndarray] = []
    labels: list[str] = []
    for key in DIST_METRICS:
        col = _col(trials, key)
        if col is not None and col.size >= 2:
            series.append(col)
            labels.append(key.replace("_", "\n"))
    if not series:
        return []
    fig, ax = plt.subplots(figsize=(max(7, 1.1 * len(series)), 4.5))
    try:
        ax.boxplot(series, tick_labels=labels, showfliers=True)
    except TypeError:
        ax.boxplot(series, labels=labels, showfliers=True)
    ax.set_title("MC metric distributions (boxplot)")
    ax.tick_params(axis="x", labelsize=7)
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    out = fig_dir / "mc_metrics_box.png"
    fig.savefig(out, dpi=120)
    plt.close(fig)
    return [out]


def _metrics_hist_grid(plt: Any, fig_dir: Path, trials: list[dict[str, Any]]) -> list[Path]:
    keys = [k for k in DIST_METRICS if _col(trials, k) is not None]
    if not keys:
        return []
    ncols = 3
    nrows = int(np.ceil(len(keys) / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(4 * ncols, 2.8 * nrows), squeeze=False)
    for i, key in enumerate(keys):
        r, c = divmod(i, ncols)
        ax = axes[r][c]
        col = _col(trials, key)
        assert col is not None
        ax.hist(col, bins=min(15, max(4, len(col) // 2)), edgecolor="black", alpha=0.75)
        ax.set_title(key, fontsize=8)
        ax.tick_params(labelsize=7)
        ax.grid(True, alpha=0.3)
    for j in range(len(keys), nrows * ncols):
        r, c = divmod(j, ncols)
        axes[r][c].axis("off")
    fig.suptitle("MC multi-metric distributions")
    fig.tight_layout()
    out = fig_dir / "mc_metrics_dist.png"
    fig.savefig(out, dpi=120)
    plt.close(fig)
    return [out]


def _success_summary(plt: Any, fig_dir: Path, trials: list[dict[str, Any]]) -> list[Path]:
    n = len(trials)
    n_ok = sum(1 for t in trials if t.get("success") is True)
    n_sim = sum(1 for t in trials if t.get("sim_success") is True)
    fig, ax = plt.subplots(figsize=(5, 3.5))
    cats = ["success", "fail", "sim_ok", "sim_fail"]
    vals = [n_ok, n - n_ok, n_sim, n - n_sim]
    colors = ["#2ca02c", "#d62728", "#1f77b4", "#ff7f0e"]
    ax.bar(cats, vals, color=colors, edgecolor="k", linewidth=0.4)
    ax.set_ylabel("count")
    ax.set_title(f"MC success summary (N={n})")
    for i, v in enumerate(vals):
        ax.text(i, v + 0.05, str(v), ha="center", fontsize=9)
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    out = fig_dir / "mc_success.png"
    fig.savefig(out, dpi=120)
    plt.close(fig)
    return [out]


def _correlation_bars(plt: Any, fig_dir: Path, art: RunArtifacts) -> list[Path]:
    corr = (art.mc_summary or {}).get("correlations_vs_rmse_position") or {}
    if not corr:
        return []
    keys = [k for k in PARAM_KEYS if k in corr and corr[k] is not None]
    if not keys:
        return []
    vals = [float(corr[k]) for k in keys]
    fig, ax = plt.subplots(figsize=(6, 3.5))
    colors = ["#d62728" if v > 0 else "#1f77b4" for v in vals]
    ax.barh(keys, vals, color=colors, edgecolor="k", linewidth=0.3)
    ax.axvline(0, color="k", lw=0.8)
    ax.set_xlabel("Pearson r vs RMSE position")
    ax.set_title("MC parameter correlations")
    ax.set_xlim(-1.05, 1.05)
    ax.grid(True, axis="x", alpha=0.3)
    fig.tight_layout()
    out = fig_dir / "mc_param_corr.png"
    fig.savefig(out, dpi=120)
    plt.close(fig)
    return [out]


def _exemplar_path_overlay(
    plt: Any, fig_dir: Path, art: RunArtifacts, rmse: np.ndarray
) -> list[Path]:
    """
    Re-simulate best / median / worst trials (by RMSE) and overlay paths.

    Uses frozen study_config + (base_seed, trial_id) — same RNG as MC.
    """
    if len(art.trials) < 1 or art.t is None:
        return []
    study_path = art.run_dir / "study_config.yaml"
    if not study_path.is_file():
        return []

    order = np.argsort(rmse)
    picks: list[tuple[str, int]] = []
    picks.append(("best", int(art.trials[int(order[0])]["trial_id"])))
    mid = int(order[len(order) // 2])
    picks.append(("median", int(art.trials[mid]["trial_id"])))
    picks.append(("worst", int(art.trials[int(order[-1])]["trial_id"])))
    # de-dupe trial ids while preserving labels
    seen: set[int] = set()
    unique: list[tuple[str, int]] = []
    for label, tid in picks:
        if tid not in seen:
            unique.append((label, tid))
            seen.add(tid)

    try:
        paths = _resim_paths(art, unique)
    except Exception:
        return []
    if not paths:
        return []

    fig = plt.figure(figsize=(7, 5.5))
    ax = fig.add_subplot(111, projection="3d")
    # nominal if available
    if art.x is not None:
        p0 = ned_to_plot(art.x[:, 0:3])
        ax.plot(p0[:, 0], p0[:, 1], p0[:, 2], "k-", lw=1.2, alpha=0.5, label="nominal")
    if art.x_ref is not None:
        pref = ned_to_plot(art.x_ref[:, 0:3])
        ax.plot(pref[:, 0], pref[:, 1], pref[:, 2], "k--", lw=1, alpha=0.4, label="ref")
    colors = {"best": "#2ca02c", "median": "#1f77b4", "worst": "#d62728"}
    for label, tid, xyz in paths:
        pp = ned_to_plot(xyz)
        ax.plot(
            pp[:, 0],
            pp[:, 1],
            pp[:, 2],
            color=colors.get(label, "C0"),
            lw=1.8,
            label=f"{label} (trial {tid})",
        )
    ax.set_xlabel("N [m]")
    ax.set_ylabel("E [m]")
    ax.set_zlabel("up [m]")
    ax.legend(fontsize=7)
    ax.set_title("MC exemplar trajectories (re-sim best/median/worst)")
    out = fig_dir / "mc_exemplar_paths.png"
    fig.savefig(out, dpi=130)
    plt.close(fig)
    return [out]


def _resim_paths(
    art: RunArtifacts, picks: list[tuple[str, int]]
) -> list[tuple[str, int, np.ndarray]]:
    """Return (label, trial_id, position_ned Nx3) for each pick."""
    import yaml

    from uavsim.control.factory import build_controller_from_mapping
    from uavsim.monte_carlo.perturb import perturb_vehicle
    from uavsim.studies.config import StudyConfig, guidance_mission_dict
    from uavsim.studies.pipeline import PreparedStudy, _build_guidance, run_closed_loop_trial
    from uavsim.vehicles.params import load_vehicle

    raw = yaml.safe_load((art.run_dir / "study_config.yaml").read_text(encoding="utf-8"))
    cfg = StudyConfig.model_validate(raw)
    # Resolve vehicle path like load_study
    vpath = Path(cfg.vehicle)
    if not vpath.is_file():
        vpath = Path.cwd() / vpath
    if not vpath.is_file():
        return []
    vehicle = load_vehicle(vpath)
    controller = build_controller_from_mapping(cfg.controller, vehicle)
    backend = _build_guidance(cfg)
    # mission file may be absolute already from original load
    plan = backend.plan(guidance_mission_dict(cfg), vehicle)
    if cfg.initial_state is not None:
        x0 = cfg.initial_state.to_array()
    else:
        x0 = plan.reference.evaluate(plan.reference.t0).x_ref.copy()

    prepared = PreparedStudy(
        cfg=cfg,
        vehicle_nominal=vehicle,
        vehicle_path=vpath,
        cfg_hash="viz",
        controller=controller,
        reference=plan.reference,
        feasibility=plan.feasibility,
        plan_diagnostics=plan.diagnostics,
        x0=x0,
    )
    base_seed = int(cfg.seed)
    out: list[tuple[str, int, np.ndarray]] = []
    for label, tid in picks:
        plant, _ = perturb_vehicle(
            vehicle, base_seed=base_seed, trial_id=tid, spec=cfg.monte_carlo.perturbation_spec()
        )
        if cfg.monte_carlo.redesign_controller:
            ctrl = build_controller_from_mapping(cfg.controller, plant)
        else:
            ctrl = controller
        sim, _metrics = run_closed_loop_trial(prepared, plant, controller=ctrl)
        out.append((label, tid, sim.x[:, 0:3].copy()))
    return out


def write_mc_dashboard_html(art: RunArtifacts, out_path: Path | None = None) -> Path:
    """Interactive Plotly MC dashboard (distributions + param scatters)."""
    try:
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
    except ImportError as exc:
        msg = "plotly is required for MC dashboard (uv sync --extra viz)"
        raise ImportError(msg) from exc

    if not art.trials:
        msg = "No MC trials to plot"
        raise FileNotFoundError(msg)

    out_path = out_path or (art.run_dir / "figures" / "mc_dashboard.html")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    rmse = _col(art.trials, "rmse_position_m")
    if rmse is None:
        msg = "trials missing rmse_position_m"
        raise FileNotFoundError(msg)

    # Layout: 2x2 main + param scatter row
    param_cols = [(k, _col(art.trials, k)) for k in PARAM_KEYS]
    param_cols = [(k, c) for k, c in param_cols if c is not None]
    n_params = max(len(param_cols), 1)

    fig = make_subplots(
        rows=2,
        cols=2,
        subplot_titles=(
            "RMSE histogram",
            "RMSE CDF",
            "Success counts",
            "RMSE vs trial_id",
        ),
    )
    nbins = min(20, max(5, len(rmse) // 2))
    fig.add_trace(go.Histogram(x=rmse, name="RMSE", nbinsx=nbins), row=1, col=1)
    s = np.sort(rmse)
    y = np.arange(1, s.size + 1) / s.size
    fig.add_trace(go.Scatter(x=s, y=y, mode="lines", name="CDF", line_shape="hv"), row=1, col=2)

    n_ok = sum(1 for t in art.trials if t.get("success") is True)
    fig.add_trace(
        go.Bar(x=["success", "fail"], y=[n_ok, len(art.trials) - n_ok], name="success"),
        row=2,
        col=1,
    )
    tids = _col(art.trials, "trial_id")
    if tids is not None:
        fig.add_trace(
            go.Scatter(x=tids, y=rmse, mode="markers", name="RMSE by trial"),
            row=2,
            col=2,
        )

    fig.update_layout(
        title=f"MC dashboard — {art.study_id} (N={len(art.trials)})",
        height=700,
        showlegend=False,
    )
    fig.write_html(str(out_path), include_plotlyjs="cdn", full_html=True)

    # Second HTML: param sensitivity multipanel
    if param_cols:
        sens_path = out_path.parent / "mc_sensitivity.html"
        ncols = min(3, n_params)
        nrows = int(np.ceil(n_params / ncols))
        fig2 = make_subplots(
            rows=nrows,
            cols=ncols,
            subplot_titles=[k for k, _ in param_cols],
        )
        for i, (key, col) in enumerate(param_cols):
            r, c = divmod(i, ncols)
            fig2.add_trace(
                go.Scatter(
                    x=col,
                    y=rmse,
                    mode="markers",
                    marker={"size": 7, "opacity": 0.75},
                    name=key,
                ),
                row=r + 1,
                col=c + 1,
            )
            fig2.update_xaxes(title_text=key, row=r + 1, col=c + 1)
            fig2.update_yaxes(title_text="RMSE [m]", row=r + 1, col=c + 1)
        fig2.update_layout(
            title=f"MC param sensitivity — {art.study_id}",
            height=280 * nrows,
            showlegend=False,
        )
        fig2.write_html(str(sens_path), include_plotlyjs="cdn", full_html=True)

    return out_path
