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

# Portfolio base case — estimation teaching matrix + ideal LQR + PID + MC
# (relative study path, gallery id, role)
BASE_CASE_STUDIES: tuple[tuple[str, str, str], ...] = (
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
        "configs/studies/figure_eight_imu_only_lqg.yaml",
        "imu_only_lqg",
        "est_imu_only_lqg",
    ),
    ("configs/studies/figure_eight_pid.yaml", "figure_eight_pid", "tracking_pid"),
    (
        "configs/studies/figure_eight_gps_imu_lqg_mc.yaml",
        "gps_imu_lqg_mc",
        "monte_carlo",
    ),
)

# Browser payload cap (full n_trials still reported in mc.n_trials / summary)
MC_TRIALS_IN_GALLERY = 400

# Teaching matrix metadata (merged into showcase.json)
ESTIMATION_MATRIX: dict[str, Any] = {
    "title": "Estimation & LQG teaching matrix",
    "description": (
        "Same elevated figure-eight and hover LQR gains. "
        "Ideal LQR sees full true state. "
        "GPS+IMU measures noisy position + body rates only. "
        "Naive packs those into the control bus with zeros elsewhere; "
        "LQG runs a linear KF (hover A,B) then the same K on x_hat. "
        "AHRS-like = attitude + rates (GPS-denied with an attitude reference). "
        "IMU-only = rates alone — position is not observable; expect drift."
    ),
    "scenarios": [
        {
            "id": "ideal",
            "label": "Ideal full state",
            "sensors": "x_true (no noise)",
            "method": "LQR",
            "run_id": "figure_eight_lqr",
            "lesson": "Upper bound when the plant is fully observed.",
        },
        {
            "id": "gps_imu_naive",
            "label": "GPS + IMU — naive",
            "sensors": "pos + omega (noisy)",
            "method": "partial_raw → LQR",
            "run_id": "gps_imu_naive",
            "lesson": "Incomplete bus (zeros for att/vel) breaks hover LQR.",
        },
        {
            "id": "gps_imu_lqg",
            "label": "GPS + IMU — LQG",
            "sensors": "pos + omega (noisy)",
            "method": "linear_kf → LQR",
            "run_id": "gps_imu_lqg",
            "lesson": "State reconstruction + noise rejection recovers tracking.",
        },
        {
            "id": "ahrs_lqg",
            "label": "GPS-denied AHRS — LQG",
            "sensors": "att + omega (noisy)",
            "method": "linear_kf → LQR",
            "run_id": "ahrs_lqg",
            "lesson": (
                "No GPS: attitude+rates still let the KF help; "
                "position tracking degrades but stays finite vs naive blow-up."
            ),
        },
        {
            "id": "imu_only_lqg",
            "label": "GPS-denied IMU-only — LQG",
            "sensors": "omega only (noisy)",
            "method": "linear_kf → LQR",
            "run_id": "imu_only_lqg",
            "lesson": (
                "Honesty case: rates alone do not observe position; "
                "filter cannot invent GPS — soft failure / drift."
            ),
        },
    ],
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
    max_points: int = 160,
) -> dict[str, Any]:
    """Serialize one run dir to JSON-friendly dict (downsampled timeseries)."""
    art = load_run(run_dir)
    gid = gallery_id or art.study_id
    entry: dict[str, Any] = {
        "id": gid,
        "label": label or art.study_id,
        "role": role,
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

    # Attach metrics into estimation matrix rows when present
    est = None
    if estimation_matrix is not None:
        est = dict(estimation_matrix)
        scenarios = []
        for sc in estimation_matrix.get("scenarios") or []:
            row = dict(sc)
            rid = row.get("run_id")
            if rid and rid in by_id:
                m = by_id[rid].get("metrics") or {}
                row["metrics"] = {
                    "rmse_position_m": m.get("rmse_position_m"),
                    "max_position_error_m": m.get("max_position_error_m"),
                    "success": m.get("success"),
                    "observer_id": m.get("observer_id"),
                    "peak_tilt_deg": (
                        float(m["peak_tilt_rad"]) * 180.0 / 3.141592653589793
                        if m.get("peak_tilt_rad") is not None
                        else None
                    ),
                }
            scenarios.append(row)
        est["scenarios"] = scenarios

    tabs = ["overview", "estimation", "flight", "metrics", "monte_carlo", "compare"]
    if envelope is not None:
        tabs.append("envelope")

    return {
        "schema_version": GALLERY_SCHEMA,
        "title": title,
        "description": description,
        "generated_at": datetime.now(UTC).isoformat(),
        "uavsim_version": __version__,
        "runs": runs,
        "compare": compare,
        "envelope": envelope,
        "estimation_matrix": est,
        "ui": {
            "default_run": runs[0]["id"] if runs else None,
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


def generate_base_case_gallery(
    *,
    repo_root: str | Path | None = None,
    out_dir: str | Path | None = None,
    runs_tmp: str | Path | None = None,
    max_points: int = 200,
    n_mc_trials: int | None = None,
    skip_envelope: bool = False,
    envelope_time_scales: tuple[float, ...] | None = None,
) -> Path:
    """
    Run the portfolio base-case studies and write ``docs/showcase``.

    Base case:
      1. Ideal full-state LQR
      2–5. Estimation matrix (GPS+IMU naive/LQG, AHRS LQG, IMU-only LQG)
      6. PID cascade
      7. Monte Carlo on GPS+IMU LQG
      8. Envelope: time-scale limits of idealized full-state LQR

    ``n_mc_trials`` overrides the study YAML when set (useful for smoke tests).
    """
    from uavsim.studies import run_nominal_study
    from uavsim.studies.envelope import SHOWCASE_TIME_SCALES, run_linearization_envelope

    root = Path(repo_root or Path.cwd()).resolve()
    out = Path(out_dir or (root / "docs" / "showcase")).resolve()
    tmp = Path(runs_tmp or (root / "runs" / "_showcase_build")).resolve()
    tmp.mkdir(parents=True, exist_ok=True)

    entries: list[dict[str, Any]] = []
    labels = {
        "figure_eight_lqr": "Ideal LQR (full state)",
        "gps_imu_naive": "GPS+IMU — naive partial LQR",
        "gps_imu_lqg": "GPS+IMU — LQG",
        "ahrs_lqg": "GPS-denied AHRS — LQG",
        "imu_only_lqg": "GPS-denied IMU-only — LQG",
        "figure_eight_pid": "PID cascade (full state)",
        "gps_imu_lqg_mc": "GPS+IMU LQG Monte Carlo",
    }
    for rel, gid, role in BASE_CASE_STUDIES:
        study = root / rel
        if not study.is_file():
            msg = f"Base-case study missing: {study}"
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
                max_points=max_points,
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
            laws=(("lqr", "none"), ("lqg", "linear_kf")),
            output_root=tmp / "envelope",
        )
        envelope_doc["title"] = "Limits of hover-linearized LQR (ideal full state)"
        envelope_doc["description"] = (
            "Time-scale τ on the figure-eight (τ=1 portfolio path). "
            "Primary story: idealized full-state LQR designed on hover A,B — "
            "where tracking fails as speed/tilt leave the linearization. "
            "LQG (full-channel KF) is shown as a secondary overlay; "
            "it is not the sensor-reconstruction teaching case (see Estimation tab)."
        )

    doc = build_gallery_document(
        entries,
        title="uavsim · flight results",
        description=(
            "Figure-eight SIL: ideal LQR, estimation/LQG sensor matrix "
            "(GPS+IMU naive vs LQG, GPS-denied AHRS and IMU-only), PID, "
            "Monte Carlo on GPS+IMU LQG, and a time-scale envelope for "
            "hover-linearization limits. Simulation only."
        ),
        # Primary compare: naive vs LQG on same sensors (teaching win)
        compare_ids=("gps_imu_naive", "gps_imu_lqg"),
        envelope=envelope_doc,
        estimation_matrix=ESTIMATION_MATRIX,
    )
    write_gallery(doc, out, copy_app=True, template_dir=root / "docs" / "showcase")
    meta = {
        "schema_version": GALLERY_SCHEMA,
        "generated_at": doc["generated_at"],
        "uavsim_version": __version__,
        "runs": [e["id"] for e in entries],
        "has_envelope": envelope_doc is not None,
        "command": "uavsim gallery --base-case",
    }
    with (out / "data" / "meta.json").open("w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
        f.write("\n")
    return out / "data" / "showcase.json"
