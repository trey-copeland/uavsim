"""Export run artifacts to a browser-ready gallery payload (React showcase)."""

from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from uavsim import __version__
from uavsim.viz.compare import compute_metric_deltas
from uavsim.viz.loaders import load_run, ned_to_plot

GALLERY_SCHEMA = 1

# Portfolio base case — controller × sensor estimation matrix + MC
# (relative study path, gallery id, role)
# Roles are shared across missions so the teaching matrix can rebind run_ids.
BASE_CASE_STUDIES: tuple[tuple[str, str, str], ...] = (
    # LQR / LQG row
    ("configs/studies/figure_eight.yaml", "figure_eight_lqr", "ideal_lqr"),
    (
        "configs/studies/figure_eight_gps_imu_naive.yaml",
        "gps_imu_naive",
        "est_gps_imu_naive",
    ),
    (
        "configs/studies/figure_eight_gps_imu_lqg.yaml",
        "gps_imu_lqg",
        "est_gps_imu_lqg",
    ),
    (
        "configs/studies/figure_eight_ahrs_lqg.yaml",
        "ahrs_lqg",
        "est_ahrs_lqg",
    ),
    (
        "configs/studies/figure_eight_flow_alt_lqg.yaml",
        "flow_alt_lqg",
        "est_flow_alt_lqg",
    ),
    (
        "configs/studies/figure_eight_imu_only_lqg.yaml",
        "imu_only_lqg",
        "est_imu_only_lqg",
    ),
    # PID row (same sensors / observers as LQR family)
    ("configs/studies/figure_eight_pid.yaml", "figure_eight_pid", "ideal_pid"),
    (
        "configs/studies/figure_eight_gps_imu_naive_pid.yaml",
        "gps_imu_naive_pid",
        "est_gps_imu_naive_pid",
    ),
    (
        "configs/studies/figure_eight_gps_imu_kf_pid.yaml",
        "gps_imu_kf_pid",
        "est_gps_imu_kf_pid",
    ),
    (
        "configs/studies/figure_eight_ahrs_kf_pid.yaml",
        "ahrs_kf_pid",
        "est_ahrs_kf_pid",
    ),
    (
        "configs/studies/figure_eight_flow_alt_kf_pid.yaml",
        "flow_alt_kf_pid",
        "est_flow_alt_kf_pid",
    ),
    (
        "configs/studies/figure_eight_imu_only_kf_pid.yaml",
        "imu_only_kf_pid",
        "est_imu_only_kf_pid",
    ),
    (
        "configs/studies/figure_eight_gps_imu_lqg_mc.yaml",
        "gps_imu_lqg_mc",
        "monte_carlo",
    ),
)

# Near-envelope twin matrix (τ★ + scheduled yaw) — same roles, edge_ run ids
EDGE_CASE_STUDIES: tuple[tuple[str, str, str], ...] = (
    ("configs/studies/edge_figure_eight.yaml", "edge_figure_eight_lqr", "ideal_lqr"),
    (
        "configs/studies/edge_gps_imu_naive.yaml",
        "edge_gps_imu_naive",
        "est_gps_imu_naive",
    ),
    (
        "configs/studies/edge_gps_imu_lqg.yaml",
        "edge_gps_imu_lqg",
        "est_gps_imu_lqg",
    ),
    ("configs/studies/edge_ahrs_lqg.yaml", "edge_ahrs_lqg", "est_ahrs_lqg"),
    (
        "configs/studies/edge_flow_alt_lqg.yaml",
        "edge_flow_alt_lqg",
        "est_flow_alt_lqg",
    ),
    (
        "configs/studies/edge_imu_only_lqg.yaml",
        "edge_imu_only_lqg",
        "est_imu_only_lqg",
    ),
    (
        "configs/studies/edge_figure_eight_pid.yaml",
        "edge_figure_eight_pid",
        "ideal_pid",
    ),
    (
        "configs/studies/edge_gps_imu_naive_pid.yaml",
        "edge_gps_imu_naive_pid",
        "est_gps_imu_naive_pid",
    ),
    (
        "configs/studies/edge_gps_imu_kf_pid.yaml",
        "edge_gps_imu_kf_pid",
        "est_gps_imu_kf_pid",
    ),
    (
        "configs/studies/edge_ahrs_kf_pid.yaml",
        "edge_ahrs_kf_pid",
        "est_ahrs_kf_pid",
    ),
    (
        "configs/studies/edge_flow_alt_kf_pid.yaml",
        "edge_flow_alt_kf_pid",
        "est_flow_alt_kf_pid",
    ),
    (
        "configs/studies/edge_imu_only_kf_pid.yaml",
        "edge_imu_only_kf_pid",
        "est_imu_only_kf_pid",
    ),
    (
        "configs/studies/edge_gps_imu_lqg_mc.yaml",
        "edge_gps_imu_lqg_mc",
        "monte_carlo",
    ),
)

MISSION_BASELINE = "baseline"
MISSION_ENVELOPE_EDGE = "envelope_edge"

_BASELINE_LABELS: dict[str, str] = {
    "figure_eight_lqr": "Ideal LQR (full state)",
    "gps_imu_naive": "GPS+IMU naive → LQR",
    "gps_imu_lqg": "GPS+IMU LQG",
    "ahrs_lqg": "AHRS LQG",
    "flow_alt_lqg": "Flow+alt LQG",
    "imu_only_lqg": "IMU-only LQG",
    "figure_eight_pid": "Ideal PID (full state)",
    "gps_imu_naive_pid": "GPS+IMU naive → PID",
    "gps_imu_kf_pid": "GPS+IMU KF → PID",
    "ahrs_kf_pid": "AHRS KF → PID",
    "flow_alt_kf_pid": "Flow+alt KF → PID",
    "imu_only_kf_pid": "IMU-only KF → PID",
    "gps_imu_lqg_mc": "GPS+IMU LQG Monte Carlo",
}

_EDGE_LABELS: dict[str, str] = {
    "edge_figure_eight_lqr": "Ideal LQR · edge",
    "edge_gps_imu_naive": "GPS+IMU naive → LQR · edge",
    "edge_gps_imu_lqg": "GPS+IMU LQG · edge",
    "edge_ahrs_lqg": "AHRS LQG · edge",
    "edge_flow_alt_lqg": "Flow+alt LQG · edge",
    "edge_imu_only_lqg": "IMU-only LQG · edge",
    "edge_figure_eight_pid": "Ideal PID · edge",
    "edge_gps_imu_naive_pid": "GPS+IMU naive → PID · edge",
    "edge_gps_imu_kf_pid": "GPS+IMU KF → PID · edge",
    "edge_ahrs_kf_pid": "AHRS KF → PID · edge",
    "edge_flow_alt_kf_pid": "Flow+alt KF → PID · edge",
    "edge_imu_only_kf_pid": "IMU-only KF → PID · edge",
    "edge_gps_imu_lqg_mc": "GPS+IMU LQG MC · edge",
}

# Browser payload cap (full n_trials still reported in mc.n_trials / summary)
MC_TRIALS_IN_GALLERY = 400

# Sensor columns for overview grid (controller × sensors)
_EST_COLUMNS: list[dict[str, str]] = [
    {"id": "ideal", "label": "Ideal full state", "sensors": "x_true (no noise)"},
    {
        "id": "gps_imu_naive",
        "label": "GPS+IMU naive",
        "sensors": "pos + omega (noisy)",
    },
    {
        "id": "gps_imu_filter",
        "label": "GPS+IMU + KF",
        "sensors": "pos + omega (noisy)",
    },
    {
        "id": "ahrs",
        "label": "GPS-denied AHRS",
        "sensors": "att + omega (noisy)",
    },
    {
        "id": "flow_alt",
        "label": "GPS-denied flow+alt",
        "sensors": "body_vel + alt + omega",
    },
    {
        "id": "imu_only",
        "label": "GPS-denied IMU-only",
        "sensors": "omega only (noisy)",
    },
]


def _scenario(
    *,
    sid: str,
    column: str,
    controller: str,
    label: str,
    sensors: str,
    method: str,
    role: str,
    run_baseline: str,
    run_edge: str,
    lesson: str,
) -> dict[str, Any]:
    return {
        "id": sid,
        "column": column,
        "controller": controller,
        "label": label,
        "sensors": sensors,
        "method": method,
        "role": role,
        # Backward-compatible default (baseline); UI prefers run_id_by_mission
        "run_id": run_baseline,
        "run_id_by_mission": {
            MISSION_BASELINE: run_baseline,
            MISSION_ENVELOPE_EDGE: run_edge,
        },
        "lesson": lesson,
    }


# Teaching matrix: rows = control law family, cols = sensors.
# Run ids rebind per mission (baseline vs envelope_edge).
ESTIMATION_MATRIX: dict[str, Any] = {
    "title": "Controller × sensor teaching matrix",
    "description": (
        "Same controller × sensor layout on every mission (see Mission selector). "
        "Baseline: calm constant-yaw figure-eight. "
        "Envelope edge: τ★≈0.28 time scale + scheduled yaw — plant stress near "
        "hover-LQR linearization limits. "
        "Rows: hover LQR (with KF = classic LQG) vs PID cascade. "
        "Columns: full-state ideal, GPS+IMU naive, GPS+IMU + KF, AHRS-like (att+ω), "
        "optical-flow proxy + altitude + gyro (body_vel+alt+ω), IMU-only (ω). "
        "KF uses the hover linear model; it does not invent GPS. "
        "Flow+alt is the practical GPS-denied win over AHRS/IMU-only. "
        "Compare laws down a column — and missions via the selector."
    ),
    "columns": _EST_COLUMNS,
    "rows": [
        {"id": "lqr", "label": "LQR / LQG", "controller": "lqr"},
        {"id": "pid", "label": "PID cascade", "controller": "pid"},
    ],
    "scenarios": [
        # —— LQR row ——
        _scenario(
            sid="ideal_lqr",
            column="ideal",
            controller="lqr",
            label="Ideal LQR",
            sensors="x_true (no noise)",
            method="LQR",
            role="ideal_lqr",
            run_baseline="figure_eight_lqr",
            run_edge="edge_figure_eight_lqr",
            lesson="Upper bound when the plant is fully observed.",
        ),
        _scenario(
            sid="gps_imu_naive_lqr",
            column="gps_imu_naive",
            controller="lqr",
            label="GPS+IMU naive → LQR",
            sensors="pos + omega (noisy)",
            method="partial_raw → LQR",
            role="est_gps_imu_naive",
            run_baseline="gps_imu_naive",
            run_edge="edge_gps_imu_naive",
            lesson="Incomplete bus (zeros for att/vel) breaks hover LQR.",
        ),
        _scenario(
            sid="gps_imu_lqg",
            column="gps_imu_filter",
            controller="lqr",
            label="GPS+IMU LQG",
            sensors="pos + omega (noisy)",
            method="linear_kf → LQR",
            role="est_gps_imu_lqg",
            run_baseline="gps_imu_lqg",
            run_edge="edge_gps_imu_lqg",
            lesson="State reconstruction + noise rejection recovers tracking.",
        ),
        _scenario(
            sid="ahrs_lqg",
            column="ahrs",
            controller="lqr",
            label="AHRS LQG",
            sensors="att + omega (noisy)",
            method="linear_kf → LQR",
            role="est_ahrs_lqg",
            run_baseline="ahrs_lqg",
            run_edge="edge_ahrs_lqg",
            lesson=(
                "No GPS: attitude+rates keep the vehicle finite, but multi-meter path "
                "error fails tracking success (3× bound). Not a navigable GPS-denied story."
            ),
        ),
        _scenario(
            sid="flow_alt_lqg",
            column="flow_alt",
            controller="lqr",
            label="Flow+alt LQG",
            sensors="body_vel + alt + omega",
            method="linear_kf → LQR",
            role="est_flow_alt_lqg",
            run_baseline="flow_alt_lqg",
            run_edge="edge_flow_alt_lqg",
            lesson=(
                "Practical GPS-denied teaching stack: body-velocity proxy "
                "(optical-flow stand-in; KF H is hover-linear) + altitude + gyro. "
                "LQG here = linear KF + hover LQR on x_hat — not classical LQG design."
            ),
        ),
        _scenario(
            sid="imu_only_lqg",
            column="imu_only",
            controller="lqr",
            label="IMU-only LQG",
            sensors="omega only (noisy)",
            method="linear_kf → LQR",
            role="est_imu_only_lqg",
            run_baseline="imu_only_lqg",
            run_edge="edge_imu_only_lqg",
            lesson=(
                "Honesty case: rates alone do not observe position; "
                "filter cannot invent GPS — soft failure / drift."
            ),
        ),
        # —— PID row ——
        _scenario(
            sid="ideal_pid",
            column="ideal",
            controller="pid",
            label="Ideal PID",
            sensors="x_true (no noise)",
            method="PID cascade",
            role="ideal_pid",
            run_baseline="figure_eight_pid",
            run_edge="edge_figure_eight_pid",
            lesson="Full-state PID on the same path (second controller baseline).",
        ),
        _scenario(
            sid="gps_imu_naive_pid",
            column="gps_imu_naive",
            controller="pid",
            label="GPS+IMU naive → PID",
            sensors="pos + omega (noisy)",
            method="partial_raw → PID",
            role="est_gps_imu_naive_pid",
            run_baseline="gps_imu_naive_pid",
            run_edge="edge_gps_imu_naive_pid",
            lesson="Same incomplete bus as LQR naive — cascade also suffers zeros.",
        ),
        _scenario(
            sid="gps_imu_kf_pid",
            column="gps_imu_filter",
            controller="pid",
            label="GPS+IMU KF → PID",
            sensors="pos + omega (noisy)",
            method="linear_kf → PID",
            role="est_gps_imu_kf_pid",
            run_baseline="gps_imu_kf_pid",
            run_edge="edge_gps_imu_kf_pid",
            lesson="KF feeds x_hat to PID (not LQG; law is cascade, not K).",
        ),
        _scenario(
            sid="ahrs_kf_pid",
            column="ahrs",
            controller="pid",
            label="AHRS KF → PID",
            sensors="att + omega (noisy)",
            method="linear_kf → PID",
            role="est_ahrs_kf_pid",
            run_baseline="ahrs_kf_pid",
            run_edge="edge_ahrs_kf_pid",
            lesson="GPS-denied with attitude reference; compare RMSE to AHRS LQG.",
        ),
        _scenario(
            sid="flow_alt_kf_pid",
            column="flow_alt",
            controller="pid",
            label="Flow+alt KF → PID",
            sensors="body_vel + alt + omega",
            method="linear_kf → PID",
            role="est_flow_alt_kf_pid",
            run_baseline="flow_alt_kf_pid",
            run_edge="edge_flow_alt_kf_pid",
            lesson="Same flow+alt sensors as LQG column; cascade on x_hat.",
        ),
        _scenario(
            sid="imu_only_kf_pid",
            column="imu_only",
            controller="pid",
            label="IMU-only KF → PID",
            sensors="omega only (noisy)",
            method="linear_kf → PID",
            role="est_imu_only_kf_pid",
            run_baseline="imu_only_kf_pid",
            run_edge="edge_imu_only_kf_pid",
            lesson="Same observability wall as LQG: rates alone cannot hold position.",
        ),
    ],
}


def _metrics_slice(m: dict[str, Any]) -> dict[str, Any]:
    return {
        "rmse_position_m": m.get("rmse_position_m"),
        "max_position_error_m": m.get("max_position_error_m"),
        "time_in_bounds_frac": m.get("time_in_bounds_frac"),
        "position_bound_m": m.get("position_bound_m"),
        "success": m.get("success"),
        "success_pos_limit_m": m.get("success_pos_limit_m"),
        "observer_id": m.get("observer_id"),
        "peak_tilt_deg": (
            float(m["peak_tilt_rad"]) * 180.0 / 3.141592653589793
            if m.get("peak_tilt_rad") is not None
            else None
        ),
        "rmse_attitude_rad": m.get("rmse_attitude_rad"),
    }


def _downsample(n: int, max_points: int) -> np.ndarray:
    if n <= max_points:
        return np.arange(n)
    return np.unique(np.linspace(0, n - 1, max_points).astype(int))


def run_to_gallery_entry(
    run_dir: str | Path,
    *,
    gallery_id: str | None = None,
    label: str | None = None,
    role: str = "run",
    mission_id: str | None = None,
    max_points: int = 160,
) -> dict[str, Any]:
    """Serialize one run dir to JSON-friendly dict (downsampled timeseries)."""
    art = load_run(run_dir)
    gid = gallery_id or art.study_id
    entry: dict[str, Any] = {
        "id": gid,
        "label": label or art.study_id,
        "role": role,
        "mission_id": mission_id,
        "study_id": art.study_id,
        "source_run": str(Path(run_dir).name),
        "metrics": art.metrics,
        "feasibility": art.feasibility,
        "manifest": {
            "seed": (art.manifest or {}).get("seed"),
            "status": (art.manifest or {}).get("status"),
            "execution": (art.manifest or {}).get("execution"),
        },
        "limits": {
            "thrust_min_n": art.limits.thrust_min_n,
            "thrust_max_n": (
                None if not np.isfinite(art.limits.thrust_max_n) else art.limits.thrust_max_n
            ),
            "torque_max_nm": (
                None if not np.isfinite(art.limits.torque_max_nm) else art.limits.torque_max_nm
            ),
        },
        "timeseries": None,
        "mc": None,
    }

    if art.t is not None and art.x is not None and art.u is not None:
        idx = _downsample(art.t.size, max_points)
        t = art.t[idx]
        x = art.x[idx]
        u = art.u[idx]
        pos_plot = ned_to_plot(x[:, 0:3])
        ts: dict[str, Any] = {
            "t": t.tolist(),
            "pos_ned": x[:, 0:3].tolist(),
            "pos_plot": pos_plot.tolist(),  # N, E, up
            "vel_ned": x[:, 6:9].tolist(),
            "euler_deg": np.rad2deg(x[:, 3:6]).tolist(),
            "omega": x[:, 9:12].tolist(),
            "u": u.tolist(),
        }
        if art.t_ref is not None and art.x_ref is not None:
            # resample ref onto same t grid
            pref = np.zeros((idx.size, 3))
            for j, ti in enumerate(t):
                k = int(np.argmin(np.abs(art.t_ref - ti)))
                pref[j] = art.x_ref[k, 0:3]
            ts["ref_ned"] = pref.tolist()
            ts["ref_plot"] = ned_to_plot(pref).tolist()
        entry["timeseries"] = ts

    if art.trials:
        # Cap trials payload for browser (summary still reflects full N)
        trials = art.trials
        if len(trials) > MC_TRIALS_IN_GALLERY:
            trials = trials[:MC_TRIALS_IN_GALLERY]
        entry["mc"] = {
            "summary": art.mc_summary,
            "trials": trials,
            "n_trials": len(art.trials),
            "n_trials_in_payload": len(trials),
        }
    return entry


def build_gallery_document(
    runs: list[dict[str, Any]],
    *,
    title: str = "uavsim · flight results",
    description: str = "",
    compare_ids: tuple[str, str] | None = None,
    envelope: dict[str, Any] | None = None,
    estimation_matrix: dict[str, Any] | None = None,
    missions: list[dict[str, Any]] | None = None,
    default_mission: str | None = None,
) -> dict[str, Any]:
    """Assemble top-level showcase.json document."""
    by_id = {r["id"]: r for r in runs}
    compare = None
    if compare_ids is not None:
        a_id, b_id = compare_ids
        if a_id in by_id and b_id in by_id:
            deltas = compute_metric_deltas(
                by_id[a_id].get("metrics") or {},
                by_id[b_id].get("metrics") or {},
            )
            compare = {
                "a": a_id,
                "b": b_id,
                "label_a": by_id[a_id]["label"],
                "label_b": by_id[b_id]["label"],
                "deltas": deltas,
            }

    # Attach metrics into estimation matrix rows (baseline + per-mission map)
    est = None
    if estimation_matrix is not None:
        est = dict(estimation_matrix)
        scenarios = []
        for sc in estimation_matrix.get("scenarios") or []:
            row = dict(sc)
            rid_map = dict(row.get("run_id_by_mission") or {})
            if not rid_map and row.get("run_id"):
                rid_map = {MISSION_BASELINE: row["run_id"]}
            metrics_by_mission: dict[str, Any] = {}
            for mid, rid in rid_map.items():
                if rid and rid in by_id:
                    metrics_by_mission[mid] = _metrics_slice(by_id[rid].get("metrics") or {})
            row["run_id_by_mission"] = rid_map
            row["metrics_by_mission"] = metrics_by_mission
            # Default metrics = baseline (or first available) for older UI paths
            default_rid = rid_map.get(MISSION_BASELINE) or row.get("run_id")
            if default_rid and default_rid in by_id:
                row["metrics"] = _metrics_slice(by_id[default_rid].get("metrics") or {})
                row["run_id"] = default_rid
            elif metrics_by_mission:
                first_mid = next(iter(metrics_by_mission))
                row["metrics"] = metrics_by_mission[first_mid]
                row["run_id"] = rid_map.get(first_mid)
            scenarios.append(row)
        est["scenarios"] = scenarios

    # Story-first order (matches showcase SPA guided path)
    tabs = ["overview", "flight", "estimation", "envelope", "monte_carlo", "compare", "metrics"]
    if envelope is None:
        tabs = [t for t in tabs if t != "envelope"]

    mission_list = list(missions or [])
    default_mid = default_mission
    if default_mid is None and mission_list:
        default_mid = mission_list[0]["id"]
    default_run = None
    if mission_list and default_mid:
        for m in mission_list:
            if m.get("id") == default_mid:
                default_run = m.get("default_run")
                break
    if default_run is None:
        default_run = runs[0]["id"] if runs else None

    return {
        "schema_version": GALLERY_SCHEMA,
        "title": title,
        "description": description,
        "generated_at": datetime.now(UTC).isoformat(),
        "uavsim_version": __version__,
        "runs": runs,
        "missions": mission_list,
        "compare": compare,
        "envelope": envelope,
        "estimation_matrix": est,
        "ui": {
            "default_run": default_run,
            "default_mission": default_mid,
            "tabs": tabs,
        },
    }


def write_gallery(
    document: dict[str, Any],
    out_dir: str | Path,
    *,
    copy_app: bool = True,
    template_dir: str | Path | None = None,
) -> Path:
    """
    Write showcase.json (+ optional static React app files) under out_dir.

    ``template_dir`` defaults to package-adjacent ``docs/showcase`` templates
    if present, else embeds minimal files from ``uavsim.viz.showcase_assets``.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    data_dir = out_dir / "data"
    data_dir.mkdir(exist_ok=True)
    path = data_dir / "showcase.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(document, f, indent=2)
        f.write("\n")

    if copy_app:
        _ensure_showcase_app(out_dir, template_dir=template_dir)
    return path


def _ensure_showcase_app(out_dir: Path, *, template_dir: Path | str | None) -> None:
    """Copy or write the React single-page app into out_dir."""
    # Prefer committed templates under docs/showcase next to data/
    candidates: list[Path] = []
    if template_dir is not None:
        candidates.append(Path(template_dir))
    # repo layout when developing
    repo_showcase = Path.cwd() / "docs" / "showcase"
    candidates.append(repo_showcase)
    # package-relative (installed wheel may not include docs — fall back to write)
    pkg = Path(__file__).resolve().parents[3] / "docs" / "showcase"
    candidates.append(pkg)

    for src in candidates:
        if (src / "index.html").is_file() and (src / "app.js").is_file():
            for name in ("index.html", "app.js", "styles.css"):
                f = src / name
                if f.is_file() and f.resolve().parent != out_dir.resolve():
                    shutil.copy2(f, out_dir / name)
            return

    # Inline fallback if templates missing
    from uavsim.viz.showcase_assets import APP_JS, INDEX_HTML, STYLES_CSS

    (out_dir / "index.html").write_text(INDEX_HTML, encoding="utf-8")
    (out_dir / "app.js").write_text(APP_JS, encoding="utf-8")
    (out_dir / "styles.css").write_text(STYLES_CSS, encoding="utf-8")


def _run_study_batch(
    *,
    root: Path,
    studies: tuple[tuple[str, str, str], ...],
    labels: dict[str, str],
    mission_id: str,
    tmp: Path,
    max_points: int,
    n_mc_trials: int | None,
) -> list[dict[str, Any]]:
    from uavsim.studies import run_nominal_study

    entries: list[dict[str, Any]] = []
    for rel, gid, role in studies:
        study = root / rel
        if not study.is_file():
            msg = f"Portfolio study missing: {study}"
            raise FileNotFoundError(msg)
        force_mc = role == "monte_carlo"
        n_override = n_mc_trials if force_mc and n_mc_trials is not None else None
        result = run_nominal_study(
            study,
            output_root=tmp,
            run_mc=force_mc if force_mc else False,
            n_trials_override=n_override,
        )
        entries.append(
            run_to_gallery_entry(
                result.run_dir,
                gallery_id=gid,
                label=labels.get(gid, gid),
                role=role,
                mission_id=mission_id,
                max_points=max_points,
            )
        )
    return entries


def generate_base_case_gallery(
    *,
    repo_root: str | Path | None = None,
    out_dir: str | Path | None = None,
    runs_tmp: str | Path | None = None,
    max_points: int = 200,
    n_mc_trials: int | None = None,
    skip_envelope: bool = False,
    envelope_time_scales: tuple[float, ...] | None = None,
    skip_edge_mission: bool = False,
) -> Path:
    """
    Run the portfolio base-case studies and write ``docs/showcase``.

    Dual-mission portfolio:
      * **baseline** — calm constant-yaw figure-eight controller × sensor matrix
      * **envelope_edge** — τ★≈0.28 + scheduled yaw twin matrix (same cells)
      Plus Monte Carlo (per mission) and the linearization envelope sweep.

    ``n_mc_trials`` overrides the study YAML when set (useful for smoke tests).
    ``skip_edge_mission`` runs only the baseline matrix (faster smoke builds).
    """
    from uavsim.studies.envelope import (
        ENVELOPE_EDGE_TIME_SCALE,
        MATRIX_SCHEMES,
        SHOWCASE_TIME_SCALES,
        run_linearization_envelope,
    )

    root = Path(repo_root or Path.cwd()).resolve()
    out = Path(out_dir or (root / "docs" / "showcase")).resolve()
    tmp = Path(runs_tmp or (root / "runs" / "_showcase_build")).resolve()
    tmp.mkdir(parents=True, exist_ok=True)

    entries: list[dict[str, Any]] = []
    entries.extend(
        _run_study_batch(
            root=root,
            studies=BASE_CASE_STUDIES,
            labels=_BASELINE_LABELS,
            mission_id=MISSION_BASELINE,
            tmp=tmp,
            max_points=max_points,
            n_mc_trials=n_mc_trials,
        )
    )
    if not skip_edge_mission:
        entries.extend(
            _run_study_batch(
                root=root,
                studies=EDGE_CASE_STUDIES,
                labels=_EDGE_LABELS,
                mission_id=MISSION_ENVELOPE_EDGE,
                tmp=tmp,
                max_points=max_points,
                n_mc_trials=n_mc_trials,
            )
        )

    envelope_doc: dict[str, Any] | None = None
    if not skip_envelope:
        scales = envelope_time_scales or SHOWCASE_TIME_SCALES
        # Emphasize idealized full-state LQR limits; LQG overlay optional contrast
        envelope_doc = run_linearization_envelope(
            repo_root=root,
            base_study_path=root / "configs" / "studies" / "figure_eight.yaml",
            time_scales=scales,
            schemes=MATRIX_SCHEMES,
            output_root=tmp / "envelope",
        )
        envelope_doc["title"] = "Controller × sensor tracking envelope"
        envelope_doc["description"] = (
            "Time-scale τ on the constant-yaw figure-eight (τ=1 portfolio baseline). "
            "Every teaching-matrix cell is swept: cascade PID and hover LQR × ideal, "
            "GPS+IMU naive, GPS+IMU KF, AHRS, flow+alt, and IMU-only. "
            "Shared position bound makes success comparable across stacks. "
            f"Portfolio envelope-edge mission (τ★≈{ENVELOPE_EDGE_TIME_SCALE:g} + scheduled yaw) "
            "is a related operating point with extra yaw demand — see Mission selector."
        )
        envelope_doc["showcase_edge_time_scale"] = ENVELOPE_EDGE_TIME_SCALE

    missions: list[dict[str, Any]] = [
        {
            "id": MISSION_BASELINE,
            "label": "Baseline figure-eight",
            "short_label": "Baseline",
            "description": (
                "Elevated figure-eight with constant yaw — calm enough that "
                "controller × sensor differences dominate over plant stress."
            ),
            "mission_file": "configs/missions/figure_eight.yaml",
            "yaw_mode": "constant",
            "time_scale": 1.0,
            "default_run": "figure_eight_lqr",
            "compare_ids": ["gps_imu_naive", "gps_imu_lqg"],
            "mc_run_id": "gps_imu_lqg_mc",
            "run_ids": [gid for _, gid, _ in BASE_CASE_STUDIES],
        },
    ]
    if not skip_edge_mission:
        missions.append(
            {
                "id": MISSION_ENVELOPE_EDGE,
                "label": "Near-envelope + scheduled yaw",
                "short_label": "Envelope edge",
                "description": (
                    f"Same geometry time-scaled by τ★≈{ENVELOPE_EDGE_TIME_SCALE:g} "
                    "(~25–30° peak tilt under ideal LQR) with from_waypoints scheduled "
                    "yaw (±~50°) so attitude is visible. Stresses hover linearization "
                    "while keeping the full controller × sensor matrix comparable."
                ),
                "mission_file": "configs/missions/figure_eight_envelope_edge.yaml",
                "yaw_mode": "from_waypoints",
                "time_scale": ENVELOPE_EDGE_TIME_SCALE,
                "default_run": "edge_figure_eight_lqr",
                "compare_ids": ["edge_gps_imu_naive", "edge_gps_imu_lqg"],
                "mc_run_id": "edge_gps_imu_lqg_mc",
                "run_ids": [gid for _, gid, _ in EDGE_CASE_STUDIES],
            }
        )

    about_paragraphs = [
        (
            "Offline SIL results for a quadrotor figure-eight: the same path flown by "
            "hover LQR and cascade PID under several sensor suites (ideal full state, "
            "GPS+IMU naive, GPS+IMU + linear KF, AHRS, optical-flow proxy + altitude, "
            "IMU-only)."
        ),
        (
            "Two missions share that geometry. Baseline uses constant yaw and the "
            "portfolio timing. Near-envelope compresses time (τ★≈0.28) and adds "
            "scheduled yaw so tilt and heading demand are visible under ideal LQR."
        ),
        (
            "Ideal full-state is the tracking upper bound. Stacks that do not observe "
            "position (or feed an incomplete state bus) are expected to exceed the "
            "position bound; those cases are included on purpose."
        ),
        (
            "Also included: Monte Carlo on GPS+IMU LQG, and a time-scale envelope over "
            "every matrix stack. Simulation only — not flight software."
        ),
    ]
    doc = build_gallery_document(
        entries,
        title="uavsim · controller × sensor flight study",
        description=" ".join(about_paragraphs),
        # Primary compare: naive vs LQG on baseline (teaching win)
        compare_ids=("gps_imu_naive", "gps_imu_lqg"),
        envelope=envelope_doc,
        estimation_matrix=ESTIMATION_MATRIX,
        missions=missions,
        default_mission=MISSION_BASELINE,
    )
    # Portfolio UX copy (guided report shell)
    doc.setdefault("ui", {})
    doc["ui"]["display_title"] = "uavsim · controller × sensor flight study"
    doc["ui"]["value_prop"] = (
        "SIL comparison of hover LQR and cascade PID under the same sensor suites."
    )
    doc["ui"]["about_paragraphs"] = about_paragraphs
    doc["ui"]["tabs"] = [
        "overview",
        "flight",
        "estimation",
        "envelope",
        "monte_carlo",
        "compare",
        "metrics",
    ]
    write_gallery(doc, out, copy_app=True, template_dir=root / "docs" / "showcase")
    meta = {
        "schema_version": GALLERY_SCHEMA,
        "generated_at": doc["generated_at"],
        "uavsim_version": __version__,
        "runs": [e["id"] for e in entries],
        "missions": [m["id"] for m in missions],
        "has_envelope": envelope_doc is not None,
        "command": "uavsim gallery --base-case",
    }
    with (out / "data" / "meta.json").open("w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
        f.write("\n")
    return out / "data" / "showcase.json"
