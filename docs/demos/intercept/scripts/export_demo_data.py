#!/usr/bin/env python3
"""Build docs/demos/intercept/data/demo.json from intercept study run directories.

Usage (from repo root)::

  uv run python docs/demos/intercept/scripts/export_demo_data.py \\
    --success-run runs/intercept_l0_success_mc_20260725T153348Z \\
    --fail-run runs/intercept_l0_fail_20260725T140842Z \\
    --with-bands --band-max-trials 100 \\
    --out docs/demos/intercept/data/demo.json

Success run may include ``monte_carlo/trials.csv`` or ``monte_carlo/shards/*/trials.csv``.
Capture KPIs use ``intercept_success`` / ``min_range_m`` — not tracking ``success``.

MC trajectory bands: with ``--with-bands`` (default when trials are present), re-simulate
selected plant-MC trials offline (fixed NDI gains) and write axis-wise p5/p50/p95
ownship paths in plot frame (N, E, up).
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "src"))

from uavsim.guidance.waypoints.backend import WaypointsGuidance  # noqa: E402
from uavsim.monte_carlo.io import read_trials_csv  # noqa: E402
from uavsim.vehicles.params import default_vehicle  # noqa: E402
from uavsim.viz.loaders import ned_to_plot  # noqa: E402

DEFAULT_TARGET = REPO_ROOT / "configs/missions/tutorials/intercept_l0_target.yaml"
DEFAULT_OUT = REPO_ROOT / "docs/demos/intercept/data/demo.json"


def _downsample_idx(n: int, max_points: int) -> np.ndarray:
    if n <= max_points:
        return np.arange(n, dtype=int)
    return np.unique(np.linspace(0, n - 1, max_points).astype(int))


def _percentile_stats(values: np.ndarray) -> dict[str, float]:
    v = np.asarray(values, dtype=float)
    v = v[np.isfinite(v)]
    if v.size == 0:
        return {
            "mean": float("nan"),
            "p50": float("nan"),
            "p95": float("nan"),
            "min": float("nan"),
            "max": float("nan"),
        }
    return {
        "mean": float(np.mean(v)),
        "p50": float(np.percentile(v, 50)),
        "p95": float(np.percentile(v, 95)),
        "min": float(np.min(v)),
        "max": float(np.max(v)),
    }


def _as_bool(val: Any) -> bool:
    if isinstance(val, bool):
        return val
    if isinstance(val, int | float):
        return bool(val)
    s = str(val).strip().lower()
    return s in {"1", "true", "yes", "y", "t"}


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, dict) else None


def _load_target_path(
    t: np.ndarray,
    target_mission: Path,
) -> np.ndarray:
    vehicle = default_vehicle()
    backend = WaypointsGuidance(method="interp", yaw_mode="from_waypoints", sample_dt_s=0.01)
    plan = backend.plan({"mission_file": str(target_mission)}, vehicle)
    return np.vstack([plan.reference.evaluate(float(ti)).x_ref[0:3] for ti in t])


def _resolve_timeseries(run_dir: Path) -> Path:
    p = run_dir / "nominal" / "timeseries.npz"
    if p.is_file():
        return p
    found = list(run_dir.glob("**/timeseries.npz"))
    if not found:
        raise FileNotFoundError(f"no timeseries.npz under {run_dir}")
    return found[0]


def load_case_pack(
    run_dir: Path,
    *,
    case_id: str,
    label: str,
    target_mission: Path,
    capture_radius_m: float,
    max_points: int,
) -> dict[str, Any]:
    run_dir = Path(run_dir)
    npz_path = _resolve_timeseries(run_dir)
    data = np.load(npz_path)
    t_full = np.asarray(data["t"], dtype=float)
    x_full = np.asarray(data["x"], dtype=float)

    metrics = _load_json(run_dir / "nominal" / "metrics.json") or {}
    capture = _load_json(run_dir / "nominal" / "intercept_capture.json") or {}

    target_full = _load_target_path(t_full, target_mission)
    range_full = np.linalg.norm(x_full[:, 0:3] - target_full, axis=1)
    i_min = int(np.argmin(range_full))
    min_range = float(range_full[i_min])
    t_min = float(t_full[i_min])
    intercept_ok = bool(min_range <= capture_radius_m)

    # Prefer metrics written by pipeline / intercept_capture when present
    min_range = float(metrics.get("min_range_m", capture.get("min_range_m", min_range)))
    t_min = float(metrics.get("time_of_min_range_s", capture.get("time_of_min_range_s", t_min)))
    if "intercept_success" in metrics:
        intercept_ok = _as_bool(metrics["intercept_success"])
    elif "intercept_success" in capture:
        intercept_ok = _as_bool(capture["intercept_success"])
    r_cap = float(
        metrics.get("capture_radius_m", capture.get("capture_radius_m", capture_radius_m))
    )
    peak_tilt = metrics.get("peak_tilt_rad", capture.get("peak_tilt_rad"))
    if peak_tilt is None and x_full.shape[1] >= 5:
        peak_tilt = float(np.max(np.maximum(np.abs(x_full[:, 3]), np.abs(x_full[:, 4]))))

    idx = _downsample_idx(t_full.size, max_points)
    t = t_full[idx]
    x = x_full[idx]
    target = target_full[idx]
    range_m = range_full[idx]
    pos_plot = ned_to_plot(x[:, 0:3])
    target_plot = ned_to_plot(target)

    case_metrics: dict[str, Any] = {
        "min_range_m": min_range,
        "time_of_min_range_s": t_min,
        "intercept_success": intercept_ok,
        "capture_radius_m": r_cap,
        "peak_tilt_rad": float(peak_tilt) if peak_tilt is not None else None,
        "peak_tilt_deg": float(np.rad2deg(float(peak_tilt))) if peak_tilt is not None else None,
        "rmse_position_m": metrics.get("rmse_position_m"),
        "success": metrics.get("success"),
        "sim_success": metrics.get("sim_success"),
        "t_final_s": float(t_full[-1]) if t_full.size else None,
    }
    # Battery metrics when pipeline logged them
    for bk in ("soc_final", "soc_min", "peak_power_w", "battery_enabled", "energy_wh_final"):
        if bk in metrics and metrics[bk] is not None:
            case_metrics[bk] = metrics[bk]

    timeseries: dict[str, Any] = {
        "t": t.tolist(),
        "pos_ned": x[:, 0:3].tolist(),
        "pos_plot": pos_plot.tolist(),
        "target_ned": target.tolist(),
        "target_plot": target_plot.tolist(),
        "range_m": range_m.tolist(),
        "euler_deg": np.rad2deg(x[:, 3:6]).tolist() if x.shape[1] >= 6 else None,
        "vel_ned": x[:, 6:9].tolist() if x.shape[1] >= 9 else None,
    }
    # Battery / energy series (same downsample index as position)
    for key in ("soc", "power_w", "energy_wh_remaining"):
        if key in data.files:
            arr = np.asarray(data[key], dtype=float)
            if arr.shape[0] == t_full.size:
                timeseries[key] = arr[idx].tolist()
            elif arr.size == t_full.size:
                timeseries[key] = arr.reshape(-1)[idx].tolist()
    # Optional wrench for attitude rotor viz
    if "u" in data.files:
        u_full = np.asarray(data["u"], dtype=float)
        if u_full.ndim == 2 and u_full.shape[0] == t_full.size:
            timeseries["u"] = u_full[idx].tolist()
    # Drop null optional arrays for smaller JSON
    timeseries = {k: v for k, v in timeseries.items() if v is not None}

    # Open-loop ownship reference if present
    ref_grid = run_dir / "reference" / "grid.npz"
    if ref_grid.is_file():
        g = np.load(ref_grid)
        t_ref = np.asarray(g["t"], dtype=float)
        x_ref = np.asarray(g["x"], dtype=float)
        pref = np.zeros((idx.size, 3))
        for j, ti in enumerate(t):
            k = int(np.argmin(np.abs(t_ref - ti)))
            pref[j] = x_ref[k, 0:3]
        timeseries["ref_ned"] = pref.tolist()
        timeseries["ref_plot"] = ned_to_plot(pref).tolist()

    return {
        "id": case_id,
        "label": label,
        "source_run": run_dir.name,
        "metrics": case_metrics,
        "timeseries": timeseries,
    }


def load_mc_trials(success_run: Path) -> list[dict[str, Any]]:
    """Load trials from merged CSV or shard CSVs under monte_carlo/."""
    mc_dir = success_run / "monte_carlo"
    merged = mc_dir / "trials.csv"
    if merged.is_file() and merged.stat().st_size > 0:
        return read_trials_csv(merged)

    shards_root = mc_dir / "shards"
    if not shards_root.is_dir():
        return []

    trials: list[dict[str, Any]] = []
    for shard in sorted(shards_root.glob("shard_*")):
        csv_path = shard / "trials.csv"
        if csv_path.is_file():
            trials.extend(read_trials_csv(csv_path))
    # de-dupe by trial_id if overlapping
    by_id: dict[int, dict[str, Any]] = {}
    for row in trials:
        tid = row.get("trial_id")
        if tid is None:
            by_id[len(by_id)] = row
            continue
        by_id[int(tid)] = row
    out = [by_id[k] for k in sorted(by_id.keys())]
    return out


def compact_trial_row(row: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "trial_id",
        "min_range_m",
        "time_of_min_range_s",
        "capture_radius_m",
        "intercept_success",
        "peak_tilt_rad",
        "rmse_position_m",
        "success",
        "sim_success",
        "mass_kg",
        "arm_length_m",
    )
    out: dict[str, Any] = {}
    for k in keys:
        if k not in row:
            continue
        v = row[k]
        if k == "intercept_success" or k == "success" or k == "sim_success":
            out[k] = _as_bool(v)
        elif k == "trial_id":
            try:
                out[k] = int(v)
            except (TypeError, ValueError):
                out[k] = v
        else:
            try:
                out[k] = float(v) if v is not None and v != "" else None
            except (TypeError, ValueError):
                out[k] = v
    return out


def _select_trial_indices(n: int, max_trials: int, seed: int) -> np.ndarray:
    """Evenly spaced subsample of trial indices (deterministic)."""
    if n <= 0:
        return np.array([], dtype=int)
    if max_trials <= 0 or n <= max_trials:
        return np.arange(n, dtype=int)
    # Stratified-ish: uniform index grid; seed only shuffles a bit for variety
    base = np.linspace(0, n - 1, max_trials)
    idx = np.unique(np.round(base).astype(int))
    if idx.size < max_trials:
        rng = np.random.default_rng(seed)
        extra = rng.choice(
            np.setdiff1d(np.arange(n), idx),
            size=min(max_trials - idx.size, n - idx.size),
            replace=False,
        )
        idx = np.sort(np.concatenate([idx, extra]))
    return idx[:max_trials]


def _float_or_none(row: dict[str, Any], key: str) -> float | None:
    v = row.get(key)
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _plant_from_trial_row(nominal: Any, row: dict[str, Any]) -> Any:
    """Build plant vehicle from trial CSV columns; fall back to re-perturb via trial_id."""
    from uavsim.vehicles.params import InertiaParams

    mass = _float_or_none(row, "mass_kg")
    ixx = _float_or_none(row, "ixx_kg_m2")
    iyy = _float_or_none(row, "iyy_kg_m2")
    izz = _float_or_none(row, "izz_kg_m2")
    arm = _float_or_none(row, "arm_length_m")
    thrust = _float_or_none(row, "thrust_max_n")

    if mass is None or ixx is None or iyy is None or izz is None or arm is None:
        return None

    thrust_max = thrust
    if thrust_max is None:
        thrust_scale = mass / nominal.mass_kg
        thrust_max = max(
            nominal.limits.thrust_max_n * thrust_scale,
            mass * nominal.gravity_m_s2 * 1.2,
        )

    updates: dict[str, Any] = {
        "mass_kg": mass,
        "arm_length_m": arm,
        "inertia": InertiaParams(ixx_kg_m2=ixx, iyy_kg_m2=iyy, izz_kg_m2=izz),
        "limits": nominal.limits.model_copy(update={"thrust_max_n": float(thrust_max)}),
    }
    tid = row.get("trial_id")
    if tid is not None:
        updates["vehicle_id"] = f"{nominal.vehicle_id}_trial{tid}"

    # Optional propulsion columns when present
    ct = _float_or_none(row, "ct_n_s2")
    cq = _float_or_none(row, "cq_nm_s2")
    mtau = _float_or_none(row, "motor_time_const_s")
    wmax = _float_or_none(row, "omega_max_rad_s")
    if any(v is not None for v in (ct, cq, mtau, wmax)):
        prop = nominal.propulsion
        updates["propulsion"] = prop.model_copy(
            update={
                "ct_n_s2": ct if ct is not None else prop.ct_n_s2,
                "cq_nm_s2": cq if cq is not None else prop.cq_nm_s2,
                "motor_time_const_s": mtau if mtau is not None else prop.motor_time_const_s,
                "omega_max_rad_s": wmax if wmax is not None else prop.omega_max_rad_s,
            }
        )
    return nominal.model_copy(update=updates)


def compute_mc_bands(
    success_run: Path,
    trials_raw: list[dict[str, Any]],
    *,
    max_trials: int,
    band_points: int,
    seed: int,
    progress: bool = True,
) -> dict[str, Any] | None:
    """Re-sim plant-MC trials and compute axis-wise ownship position percentiles."""
    import yaml

    from uavsim.control.factory import build_controller_from_mapping
    from uavsim.monte_carlo.perturb import perturb_vehicle
    from uavsim.studies.config import StudyConfig, guidance_mission_dict
    from uavsim.studies.pipeline import PreparedStudy, _build_guidance, run_closed_loop_trial
    from uavsim.vehicles.params import load_vehicle

    if not trials_raw:
        return None

    cfg_path = success_run / "study_config.yaml"
    if not cfg_path.is_file():
        print(f"warn: no study_config.yaml under {success_run}; bands skipped", file=sys.stderr)
        return None

    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    cfg = StudyConfig.model_validate(raw)

    vpath = Path(cfg.vehicle)
    if not vpath.is_file():
        vpath = (REPO_ROOT / vpath).resolve()
    if not vpath.is_file():
        vpath = (Path.cwd() / cfg.vehicle).resolve()
    if not vpath.is_file():
        print(f"warn: vehicle not found: {cfg.vehicle}; bands skipped", file=sys.stderr)
        return None

    vehicle = load_vehicle(vpath)
    controller = build_controller_from_mapping(cfg.controller, vehicle)
    backend = _build_guidance(cfg)
    plan = backend.plan(guidance_mission_dict(cfg), vehicle)
    if cfg.initial_state is not None:
        x0 = cfg.initial_state.to_array()
    else:
        x0 = plan.reference.evaluate(plan.reference.t0).x_ref.copy()

    prepared = PreparedStudy(
        cfg=cfg,
        vehicle_nominal=vehicle,
        vehicle_path=vpath,
        cfg_hash="demo_bands",
        controller=controller,
        reference=plan.reference,
        feasibility=plan.feasibility,
        plan_diagnostics=plan.diagnostics,
        x0=x0,
    )

    # Common time grid from nominal timeseries when available
    try:
        npz = np.load(_resolve_timeseries(success_run))
        t_nom = np.asarray(npz["t"], dtype=float)
    except FileNotFoundError:
        t_nom = np.asarray(
            plan.reference.t_grid if hasattr(plan.reference, "t_grid") else [], dtype=float
        )
        if t_nom.size == 0:
            t0, tf = float(plan.reference.t0), float(plan.reference.tf)
            t_nom = np.linspace(t0, tf, max(band_points, 50))

    t_grid = t_nom[_downsample_idx(t_nom.size, band_points)]
    n_grid = int(t_grid.size)

    sel = _select_trial_indices(len(trials_raw), max_trials, seed)
    paths_n = np.full((sel.size, n_grid), np.nan, dtype=float)
    paths_e = np.full((sel.size, n_grid), np.nan, dtype=float)
    paths_u = np.full((sel.size, n_grid), np.nan, dtype=float)

    base_seed = int(cfg.seed)
    redesign = bool(cfg.monte_carlo.redesign_controller)
    n_ok = 0
    t_start = time.time()

    if progress:
        print(
            f"bands: re-sim {sel.size}/{len(trials_raw)} trials "
            f"(redesign_controller={redesign}, grid={n_grid} pts)…",
            file=sys.stderr,
            flush=True,
        )

    for i, row_i in enumerate(sel):
        row = trials_raw[int(row_i)]
        plant = _plant_from_trial_row(vehicle, row)
        if plant is None:
            tid = int(row.get("trial_id", row_i))
            plant, _ = perturb_vehicle(
                vehicle,
                base_seed=base_seed,
                trial_id=tid,
                spec=cfg.monte_carlo.perturbation_spec(),
            )
        ctrl = build_controller_from_mapping(cfg.controller, plant) if redesign else controller
        try:
            sim, _metrics = run_closed_loop_trial(prepared, plant, controller=ctrl)
        except Exception as exc:  # noqa: BLE001 — one bad trial should not kill pack
            if progress:
                print(f"  trial {row.get('trial_id', row_i)} failed: {exc}", file=sys.stderr)
            continue

        t_sim = np.asarray(sim.t, dtype=float)
        pos_ned = np.asarray(sim.x[:, 0:3], dtype=float)
        if t_sim.size < 2:
            continue
        # Interpolate each NED axis onto common grid, then plot-frame
        n_i = np.interp(t_grid, t_sim, pos_ned[:, 0])
        e_i = np.interp(t_grid, t_sim, pos_ned[:, 1])
        d_i = np.interp(t_grid, t_sim, pos_ned[:, 2])
        pos_plot = ned_to_plot(np.column_stack([n_i, e_i, d_i]))
        paths_n[i, :] = pos_plot[:, 0]
        paths_e[i, :] = pos_plot[:, 1]
        paths_u[i, :] = pos_plot[:, 2]
        n_ok += 1

        if progress and ((i + 1) % 10 == 0 or i + 1 == sel.size):
            elapsed = time.time() - t_start
            rate = (i + 1) / elapsed if elapsed > 0 else 0.0
            eta = (sel.size - i - 1) / rate if rate > 0 else float("nan")
            print(
                f"  {i + 1}/{sel.size} ok={n_ok}  {elapsed:.0f}s elapsed  eta {eta:.0f}s",
                file=sys.stderr,
                flush=True,
            )

    if n_ok < 2:
        print("warn: fewer than 2 successful band re-sims; bands skipped", file=sys.stderr)
        return None

    def axis_percentiles(paths: np.ndarray) -> dict[str, list[float]]:
        # paths: (n_trials, n_grid); nan rows ignored
        p5 = np.nanpercentile(paths, 5, axis=0)
        p50 = np.nanpercentile(paths, 50, axis=0)
        p95 = np.nanpercentile(paths, 95, axis=0)
        return {
            "p5": [float(x) for x in p5],
            "p50": [float(x) for x in p50],
            "p95": [float(x) for x in p95],
        }

    # Joint horizontal radius about median path (m in plot N–E).
    # This yields a tubular / conical CI that can grow along the mission —
    # unlike independent N/E axis percentiles, which look "planar"/boxy.
    med_n = np.nanpercentile(paths_n, 50, axis=0)
    med_e = np.nanpercentile(paths_e, 50, axis=0)
    med_u = np.nanpercentile(paths_u, 50, axis=0)
    dn = paths_n - med_n
    de = paths_e - med_e
    r_horiz = np.sqrt(dn * dn + de * de)
    r68 = np.nanpercentile(r_horiz, 68, axis=0)  # ~1σ for soft inner CI
    r95 = np.nanpercentile(r_horiz, 95, axis=0)

    return {
        "frame": "plot",
        "percentiles": [5, 50, 95],
        "t": [float(x) for x in t_grid],
        "n_paths_used": int(n_ok),
        "n_paths_requested": int(sel.size),
        "method": "median_path_plus_horiz_radius",
        "notes": (
            "Median ownship path from plant re-sim; horizontal radius percentiles "
            "(distance in N–E from median) give a tubular CI (often conical as "
            "uncertainty grows). Also stores axis-wise N/E/U for diagnostics. "
            "Fixed NDI; redesign_controller=false."
        ),
        "ownship": {
            "N": axis_percentiles(paths_n),
            "E": axis_percentiles(paths_e),
            "U": axis_percentiles(paths_u),
            "median": {
                "N": [float(x) for x in med_n],
                "E": [float(x) for x in med_e],
                "U": [float(x) for x in med_u],
            },
            "radius_horiz_m": {
                "p68": [float(x) for x in r68],
                "p95": [float(x) for x in r95],
            },
        },
    }


def build_mc_block(
    success_run: Path,
    trials_raw: list[dict[str, Any]],
    capture_radius_m: float,
    *,
    bands: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    if not trials_raw:
        return None

    trials = [compact_trial_row(r) for r in trials_raw]
    n = len(trials)
    n_cap = sum(1 for r in trials if r.get("intercept_success"))
    p_capture = n_cap / n if n else float("nan")

    min_ranges = np.array(
        [float(r["min_range_m"]) for r in trials if r.get("min_range_m") is not None],
        dtype=float,
    )
    tilts = np.array(
        [float(r["peak_tilt_rad"]) for r in trials if r.get("peak_tilt_rad") is not None],
        dtype=float,
    )

    r_caps = [float(r["capture_radius_m"]) for r in trials if r.get("capture_radius_m") is not None]
    r_cap = float(r_caps[0]) if r_caps else capture_radius_m

    summary = {
        "n_trials": n,
        "n_intercept_success": n_cap,
        "p_capture": p_capture,
        "capture_radius_m": r_cap,
        "min_range_m": _percentile_stats(min_ranges),
        "peak_tilt_rad": _percentile_stats(tilts) if tilts.size else None,
        "note": (
            "P(capture) = mean(intercept_success). "
            "Tracking field `success` is not used (often false due to attitude bounds)."
        ),
    }
    if summary["peak_tilt_rad"] is None:
        del summary["peak_tilt_rad"]

    # Optional pre-binned histogram for convenience (UI can also bin trials)
    if min_ranges.size:
        hist_counts, hist_edges = np.histogram(min_ranges, bins=min(40, max(10, int(math.sqrt(n)))))
        summary["min_range_hist"] = {
            "counts": hist_counts.astype(int).tolist(),
            "bin_edges_m": hist_edges.tolist(),
        }

    mc_summary_file = _load_json(success_run / "monte_carlo" / "summary.json")

    return {
        "source_study": success_run.name,
        "n_trials": n,
        "summary": summary,
        "pipeline_summary": mc_summary_file,
        "trials": trials,
        "bands": bands,
    }


def build_demo(
    *,
    success_run: Path,
    fail_run: Path | None,
    target_mission: Path,
    capture_radius_m: float,
    max_points: int,
    uavsim_version: str,
    with_bands: bool,
    band_max_trials: int,
    band_points: int,
    band_seed: int,
) -> dict[str, Any]:
    success = load_case_pack(
        success_run,
        case_id="intercept_l0_success",
        label="Success (capture)",
        target_mission=target_mission,
        capture_radius_m=capture_radius_m,
        max_points=max_points,
    )
    fail = None
    if fail_run is not None:
        fail = load_case_pack(
            fail_run,
            case_id="intercept_l0_fail",
            label="Fail (miss)",
            target_mission=target_mission,
            capture_radius_m=capture_radius_m,
            max_points=max_points,
        )

    trials_raw = load_mc_trials(success_run)
    bands = None
    if with_bands and trials_raw:
        bands = compute_mc_bands(
            success_run,
            trials_raw,
            max_trials=band_max_trials,
            band_points=band_points,
            seed=band_seed,
        )
    mc = build_mc_block(success_run, trials_raw, capture_radius_m, bands=bands)

    r_cap = capture_radius_m
    if mc and mc.get("summary"):
        r_cap = float(mc["summary"].get("capture_radius_m", r_cap))
    elif success["metrics"].get("capture_radius_m") is not None:
        r_cap = float(success["metrics"]["capture_radius_m"])

    cases: dict[str, Any] = {"success": success}
    if fail is not None:
        cases["fail"] = fail

    has_batt = any(
        k in (success.get("timeseries") or {}) for k in ("soc", "power_w", "energy_wh_remaining")
    )

    how_to = [
        "Pad takeoff → climb through ground effect → open-loop intercept path.",
        "Plant parameter scatter only — controller gains are fixed.",
        "Capture = min range ≤ capture radius (not tracking RMSE / success flag).",
        "MC summary attaches to the success recipe; Fail toggle shows a miss nominal only.",
    ]
    if bands is not None:
        how_to.append(
            "Trajectory bands = ownship spatial p5/p50/p95 from plant re-sim "
            f"(n={bands.get('n_paths_used')}); axis-wise, not sensor noise."
        )
    if has_batt:
        how_to.append(
            "Battery SOC / power / energy series are scrub-synced when logged by the study."
        )

    about = [
        (
            "Pad climb intercept: ownship takes off from a pad, climbs through ground effect "
            "(GE), then tracks an open-loop reference toward a scripted target with fixed NDI "
            "(redesign_controller=false under plant MC). L0 is not closed-loop replan."
        ),
        (
            f"Capture criterion: min_t ‖p_own − p_tgt‖ ≤ r_capture "
            f"(default r_capture = {r_cap:g} m). KPI P(capture) uses "
            "intercept_success, not tracking success (attitude error bounds often fail)."
        ),
        (
            "Monte Carlo perturbs plant parameters only (mass, I, arm length, …). "
            "Gains stay fixed so the histogram reflects plant robustness, "
            "not retuned control. Trajectory confidence bands are offline re-sim "
            "percentiles of ownship position under that plant scatter."
        ),
    ]
    if has_batt:
        about.append(
            "Battery model enabled on this pack: SOC, electrical power, and energy remaining "
            "are downsampled with the nominal timeseries for the scrubbed energy story."
        )

    return {
        "schema_version": 1,
        "title": "uavsim · intercept L0 (NDI + plant MC)",
        "generated_at": datetime.now(UTC).isoformat(),
        "uavsim_version": uavsim_version,
        "ui": {
            "value_prop": (
                "Pad climb (ground effect) → open-loop intercept path; scripted target; "
                "fixed NDI; plant mass / inertia / arm Monte Carlo"
                + ("; battery SOC/power when logged." if has_batt else ".")
            ),
            "about_paragraphs": about,
            "capture_radius_m": r_cap,
            "default_case": "success",
            "mission_notes": "pad_climb_ground_effect",
            "how_to_read": how_to,
        },
        "cases": cases,
        "mc": mc,
    }


def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument(
        "--success-run",
        type=Path,
        required=True,
        help="Success study run dir (nominal + optional monte_carlo)",
    )
    p.add_argument(
        "--fail-run",
        type=Path,
        default=None,
        help="Optional fail nominal run dir",
    )
    p.add_argument(
        "--target-mission",
        type=Path,
        default=DEFAULT_TARGET,
        help="Scripted target mission YAML (default: intercept_l0_target)",
    )
    p.add_argument(
        "--capture-radius-m",
        type=float,
        default=1.0,
        help="Capture radius used when metrics lack intercept fields",
    )
    p.add_argument(
        "--max-points",
        type=int,
        default=320,
        help="Downsample timeseries to this many points",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help="Output demo.json path",
    )
    p.add_argument(
        "--uavsim-version",
        type=str,
        default="0.1.0",
    )
    p.add_argument(
        "--with-bands",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Re-sim MC trials and write mc.bands "
            "(default on when trials exist; --no-with-bands to skip)"
        ),
    )
    p.add_argument(
        "--band-max-trials",
        type=int,
        default=100,
        help="Max plant trials to re-sim for bands (default 100; up to full MC size)",
    )
    p.add_argument(
        "--band-points",
        type=int,
        default=160,
        help="Common time-grid length for band percentiles (default 160)",
    )
    p.add_argument(
        "--band-seed",
        type=int,
        default=0,
        help="Seed for band trial subsample when band-max-trials < n_trials",
    )
    args = p.parse_args()

    success_run = args.success_run
    if not success_run.is_dir():
        print(f"success run not found: {success_run}", file=sys.stderr)
        return 1
    if args.fail_run is not None and not args.fail_run.is_dir():
        print(f"fail run not found: {args.fail_run}", file=sys.stderr)
        return 1
    if not args.target_mission.is_file():
        print(f"target mission not found: {args.target_mission}", file=sys.stderr)
        return 1

    demo = build_demo(
        success_run=success_run,
        fail_run=args.fail_run,
        target_mission=args.target_mission,
        capture_radius_m=args.capture_radius_m,
        max_points=args.max_points,
        uavsim_version=args.uavsim_version,
        with_bands=bool(args.with_bands),
        band_max_trials=int(args.band_max_trials),
        band_points=int(args.band_points),
        band_seed=int(args.band_seed),
    )

    out = args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        json.dump(demo, f, indent=2)
        f.write("\n")

    n_mc = demo["mc"]["n_trials"] if demo.get("mc") else 0
    p_cap = demo["mc"]["summary"]["p_capture"] if demo.get("mc") else None
    bands = demo["mc"]["bands"] if demo.get("mc") else None
    cases = list(demo["cases"].keys())
    size_kb = out.stat().st_size / 1024
    band_info: dict[str, Any] | None = None
    if bands:
        band_info = {
            "n_paths_used": bands.get("n_paths_used"),
            "t_len": len(bands.get("t") or []),
            "N_p5_len": len((bands.get("ownship") or {}).get("N", {}).get("p5") or []),
        }
    print(
        json.dumps(
            {
                "wrote": str(out),
                "size_kb": round(size_kb, 1),
                "cases": cases,
                "n_mc_trials": n_mc,
                "p_capture": p_cap,
                "bands": band_info,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
