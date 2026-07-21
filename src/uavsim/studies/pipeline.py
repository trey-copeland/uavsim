"""Nominal + Monte Carlo study pipeline: config → plan → sim → metrics → run dir."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import numpy as np

from uavsim.control.export import write_controller_artifact
from uavsim.control.factory import build_controller_from_mapping, controller_artifact_for
from uavsim.control.lqr import LqrHoverController
from uavsim.control.pid import PidCascadeController
from uavsim.guidance import HoldGuidance, WaypointsGuidance
from uavsim.metrics import compute_metrics
from uavsim.monte_carlo import (
    partition_trials,
    run_monte_carlo,
    write_merged_mc_artifacts,
    write_shard_artifacts,
    write_trials_csv,
    write_trials_json,
)
from uavsim.reference import ReferenceTrajectory, SampledReference
from uavsim.results import (
    create_run_directory,
    write_json,
    write_manifest,
    write_nominal_timeseries,
    write_text_report,
    write_yaml,
)
from uavsim.sim import InProcessControllerAdapter, SimPlant, simulate_closed_loop
from uavsim.sim.closed_loop import ClosedLoopResult
from uavsim.studies.config import (
    HoldGuidanceConfig,
    StudyConfig,
    WaypointsGuidanceConfig,
    guidance_mission_dict,
    load_study,
)
from uavsim.vehicles.params import VehicleParams, load_vehicle

BackendName = Literal["local", "docker"]
AnyController = LqrHoverController | PidCascadeController


@dataclass
class StudyRunResult:
    run_dir: Path
    metrics: dict[str, Any]
    success: bool
    feasibility: dict[str, Any] | None = None
    mc_summary: dict[str, Any] | None = None
    n_trials: int = 0
    n_shards: int = 1
    backend: str = "local"


@dataclass
class PreparedStudy:
    cfg: StudyConfig
    vehicle_nominal: VehicleParams
    vehicle_path: Path
    cfg_hash: str
    controller: AnyController
    reference: ReferenceTrajectory
    feasibility: Any
    plan_diagnostics: dict[str, Any]
    x0: np.ndarray


def _build_guidance(cfg: StudyConfig) -> Any:
    g = cfg.guidance
    if isinstance(g, HoldGuidanceConfig):
        return HoldGuidance()
    if isinstance(g, WaypointsGuidanceConfig):
        return WaypointsGuidance(
            method=g.method,
            yaw_mode=g.yaw_mode,
            sample_dt_s=g.sample_dt_s,
            fail_on_infeasible=g.fail_on_infeasible,
        )
    msg = f"Unsupported guidance type: {type(g)}"
    raise TypeError(msg)


def prepare_study(cfg: StudyConfig, vehicle_path: Path, cfg_hash: str) -> PreparedStudy:
    vehicle = load_vehicle(vehicle_path)
    controller = build_controller_from_mapping(cfg.controller, vehicle)
    backend = _build_guidance(cfg)
    plan = backend.plan(guidance_mission_dict(cfg), vehicle)
    reference = plan.reference
    if cfg.initial_state is not None:
        x0 = cfg.initial_state.to_array()
    else:
        x0 = reference.evaluate(reference.t0).x_ref.copy()
    return PreparedStudy(
        cfg=cfg,
        vehicle_nominal=vehicle,
        vehicle_path=vehicle_path,
        cfg_hash=cfg_hash,
        controller=controller,
        reference=reference,
        feasibility=plan.feasibility,
        plan_diagnostics=plan.diagnostics,
        x0=x0,
    )


def run_closed_loop_trial(
    prepared: PreparedStudy,
    plant_vehicle: VehicleParams,
    controller: AnyController | None = None,
) -> tuple[ClosedLoopResult, dict[str, Any]]:
    """Simulate one closed-loop run; returns (sim_result, metrics)."""
    from uavsim.estimation import build_observer

    ctrl = controller if controller is not None else prepared.controller
    cfg = prepared.cfg
    plant = SimPlant(
        plant_vehicle,
        attitude=cfg.sim.attitude,
        plant=getattr(cfg.sim, "plant", "wrench"),
    )
    adapter = InProcessControllerAdapter(ctrl, prepared.reference)
    observer, meas_model = build_observer(cfg.sim.observer, plant_vehicle)
    sim_result = simulate_closed_loop(
        plant,
        adapter,
        t0=prepared.reference.t0,
        tf=prepared.reference.tf,
        x0=prepared.x0,
        max_step=cfg.sim.dt_s,
        rtol=cfg.sim.rtol,
        atol=cfg.sim.atol,
        observer=observer,
        measurement_model=meas_model,
    )
    metrics = compute_metrics(
        sim_result.t,
        sim_result.x,
        sim_result.u,
        prepared.reference,
        position_bound_m=cfg.metrics.position_bound_m,
    )
    metrics["sim_success"] = sim_result.success
    metrics["sim_message"] = sim_result.message
    metrics["observer_id"] = sim_result.observer_id
    metrics["sim_attitude"] = sim_result.attitude
    if sim_result.x_hat is not None and sim_result.x is not None:
        e_est = sim_result.x_hat - sim_result.x
        metrics["rmse_estimate_position_m"] = float(
            np.sqrt(np.mean(np.sum(e_est[:, 0:3] ** 2, axis=1)))
        )
        metrics["rmse_estimate_attitude_rad"] = float(
            np.sqrt(np.mean(np.sum(e_est[:, 3:6] ** 2, axis=1)))
        )
    return sim_result, metrics


def _write_reference_artifacts(run_dir: Path, prepared: PreparedStudy) -> None:
    reference = prepared.reference
    write_yaml(
        run_dir / "guidance" / "backend.yaml",
        {
            "backend_id": reference.backend_id,
            "metadata": reference.metadata,
            "diagnostics": prepared.plan_diagnostics,
            "t0": reference.t0,
            "tf": reference.tf,
        },
    )
    write_json(
        run_dir / "guidance" / "feasibility.json",
        prepared.feasibility.to_dict(),
    )
    if isinstance(reference, SampledReference):
        write_json(
            run_dir / "reference" / "sampled.json",
            {
                "backend_id": reference.backend_id,
                "t0": reference.t0,
                "tf": reference.tf,
                "n_samples": int(reference.t_grid.size),
                "dt_s": float(np.mean(np.diff(reference.t_grid)))
                if reference.t_grid.size > 1
                else None,
                "metadata": reference.metadata,
            },
        )
        np.savez_compressed(
            run_dir / "reference" / "grid.npz",
            t=reference.t_grid,
            x=reference.x_grid,
        )
    else:
        write_json(
            run_dir / "reference" / "hold.json",
            {
                "x_hold": reference.evaluate(reference.t0).x_ref.tolist(),
                "backend_id": reference.backend_id,
            },
        )


def _metric_row(metrics: dict[str, Any]) -> dict[str, Any]:
    """Flatten metrics for trial tables (skip nested/large fields)."""
    keys = (
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
        "sim_message",
    )
    return {k: metrics[k] for k in keys if k in metrics}


def _make_trial_fn(prepared: PreparedStudy):
    cfg = prepared.cfg
    redesign = cfg.monte_carlo.redesign_controller

    def trial_fn(
        trial_id: int,
        plant_vehicle: VehicleParams,
        _params: dict[str, float],
    ) -> dict[str, Any]:
        if redesign:
            ctrl = build_controller_from_mapping(cfg.controller, plant_vehicle)
        else:
            ctrl = prepared.controller
        _sim, m = run_closed_loop_trial(prepared, plant_vehicle, controller=ctrl)
        return _metric_row(m)

    return trial_fn


def run_mc_for_prepared(
    prepared: PreparedStudy,
    *,
    n_shards: int = 1,
    shards_root: Path | None = None,
    progress: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, Any], Any]:
    """
    Run MC trials for a prepared study, optionally partitioned into shards.

    When ``n_shards > 1`` and ``shards_root`` is set, intermediate shard
    artifacts are written under ``shards_root/shard_XX/``.
    """
    cfg = prepared.cfg
    n_trials = cfg.monte_carlo.n_trials
    redesign = cfg.monte_carlo.redesign_controller
    trial_fn = _make_trial_fn(prepared)
    plan = partition_trials(n_trials, n_shards)

    all_trials: list[dict[str, Any]] = []
    for shard_id in range(n_shards):
        ids = plan.trial_ids(shard_id)
        if not ids:
            shard_trials: list[dict[str, Any]] = []
        else:
            if progress and n_shards > 1:
                print(
                    f"  MC shard {shard_id + 1}/{n_shards}  "
                    f"trials {ids[0]}–{ids[-1]} ({len(ids)} runs)",
                    flush=True,
                )
            mc_result = run_monte_carlo(
                nominal_vehicle=prepared.vehicle_nominal,
                base_seed=cfg.seed,
                n_trials=n_trials,
                trial_fn=trial_fn,
                spec=cfg.monte_carlo.perturbation_spec(),
                redesign_controller=redesign,
                trial_ids=ids,
                progress=progress,
            )
            shard_trials = mc_result.trials
        all_trials.extend(shard_trials)
        if shards_root is not None and n_shards > 1:
            write_shard_artifacts(
                Path(shards_root) / f"shard_{shard_id:02d}",
                shard_id=shard_id,
                n_shards=n_shards,
                trials=shard_trials,
                plan=plan,
                extra_meta={"base_seed": cfg.seed, "study_id": cfg.study_id},
            )

    all_trials.sort(key=lambda r: int(r["trial_id"]))
    from uavsim.monte_carlo import summarize_trials

    summary = summarize_trials(all_trials)
    summary["redesign_controller"] = redesign
    summary["base_seed"] = int(cfg.seed)
    summary["n_shards"] = n_shards
    return all_trials, summary, plan


def run_mc_shard_only(
    study_path: str | Path,
    *,
    shard_id: int,
    n_shards: int,
    output_dir: str | Path,
    n_trials_override: int | None = None,
) -> Path:
    """
    Worker entry: run one shard's trials and write artifacts under ``output_dir``.

    Does not run nominal sim or write a full run directory.
    """
    cfg, vehicle_path, cfg_hash, _ = load_study(study_path)
    if n_trials_override is not None:
        cfg.monte_carlo.n_trials = n_trials_override
    if not cfg.monte_carlo.enabled:
        cfg.monte_carlo.enabled = True
    prepared = prepare_study(cfg, vehicle_path, cfg_hash)
    plan = partition_trials(cfg.monte_carlo.n_trials, n_shards)
    ids = plan.trial_ids(shard_id)
    trial_fn = _make_trial_fn(prepared)
    if ids:
        mc_result = run_monte_carlo(
            nominal_vehicle=prepared.vehicle_nominal,
            base_seed=cfg.seed,
            n_trials=cfg.monte_carlo.n_trials,
            trial_fn=trial_fn,
            spec=cfg.monte_carlo.perturbation_spec(),
            redesign_controller=cfg.monte_carlo.redesign_controller,
            trial_ids=ids,
        )
        trials = mc_result.trials
    else:
        trials = []
    out = write_shard_artifacts(
        Path(output_dir),
        shard_id=shard_id,
        n_shards=n_shards,
        trials=trials,
        plan=plan,
        extra_meta={
            "base_seed": cfg.seed,
            "study_id": cfg.study_id,
            "config_hash": cfg_hash,
        },
    )
    return out


def run_nominal_study(
    study_path: str | Path,
    *,
    output_root: str | Path = "runs",
    run_mc: bool | None = None,
    n_trials_override: int | None = None,
    backend: BackendName | None = None,
    n_shards: int | None = None,
    docker_image: str | None = None,
    repo_root: Path | None = None,
    progress: bool = False,
) -> StudyRunResult:
    """
    Run nominal SIL study (+ optional MC if config enables it).

    ``backend`` / ``n_shards`` override config when provided.
    ``docker`` backend runs the whole study inside a container (local sharding inside).
    ``progress``: print study/MC status to stdout (CLI sets True).
    """
    study_path = Path(study_path)
    cfg, vehicle_path, cfg_hash, _mission_path = load_study(study_path)
    if n_trials_override is not None:
        if n_trials_override < 1:
            msg = "n_trials_override must be >= 1"
            raise ValueError(msg)
        cfg.monte_carlo.n_trials = n_trials_override
    if n_shards is not None:
        if n_shards < 1:
            msg = "n_shards must be >= 1"
            raise ValueError(msg)
        cfg.monte_carlo.shards = n_shards
    if backend is not None:
        cfg.monte_carlo.backend = backend

    do_mc = cfg.monte_carlo.enabled if run_mc is None else run_mc
    resolved_backend: BackendName = cfg.monte_carlo.backend if do_mc else "local"
    shards = cfg.monte_carlo.shards if do_mc else 1

    # Docker path: execute study inside container with local backend
    if do_mc and resolved_backend == "docker":
        from uavsim.monte_carlo.docker_run import docker_available, docker_study

        if not docker_available():
            msg = "Docker backend requested but docker is not available"
            raise RuntimeError(msg)
        root = (repo_root or Path.cwd()).resolve()
        out = Path(output_root)
        if not out.is_absolute():
            out = (root / out).resolve()
        out.mkdir(parents=True, exist_ok=True)
        result = docker_study(
            study_path.resolve(),
            repo_root=root,
            output_root=out,
            image=docker_image,
            n_trials=cfg.monte_carlo.n_trials if n_trials_override is not None else None,
            force_mc=run_mc if run_mc is not None else (True if do_mc else None),
            shards=shards,
        )
        if result["returncode"] != 0:
            msg = (
                f"Docker study failed (code {result['returncode']}):\n"
                f"{result['stderr'] or result['stdout']}"
            )
            raise RuntimeError(msg)
        # Discover newest run dir for this study_id
        runs = sorted(out.glob(f"{cfg.study_id}_*"), key=lambda p: p.stat().st_mtime)
        if not runs:
            msg = f"Docker study succeeded but no run dir found under {out}"
            raise RuntimeError(msg)
        run_dir = runs[-1]
        metrics = {}
        metrics_path = run_dir / "nominal" / "metrics.json"
        if metrics_path.is_file():
            import json

            metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        mc_summary = None
        summary_path = run_dir / "monte_carlo" / "summary.json"
        if summary_path.is_file():
            import json

            mc_summary = json.loads(summary_path.read_text(encoding="utf-8"))
        return StudyRunResult(
            run_dir=run_dir,
            metrics=metrics,
            success=bool(metrics.get("success", True)),
            mc_summary=mc_summary,
            n_trials=int(mc_summary["n_trials"]) if mc_summary else 0,
            n_shards=shards,
            backend="docker",
        )

    plant_kind = getattr(cfg.sim, "plant", "wrench")
    if progress:
        print(
            f"[uavsim] study={cfg.study_id}  plant={plant_kind}  "
            f"attitude={cfg.sim.attitude}  seed={cfg.seed}",
            flush=True,
        )
        print("[uavsim] nominal closed-loop…", flush=True)

    prepared = prepare_study(cfg, vehicle_path, cfg_hash)
    sim_result, metrics = run_closed_loop_trial(prepared, prepared.vehicle_nominal)
    metrics["feasibility_ok"] = prepared.feasibility.ok
    overall_ok = bool(sim_result.success and metrics.get("success", False))

    if progress:
        print(
            f"[uavsim] nominal done  rmse_pos="
            f"{metrics.get('rmse_position_m', float('nan')):.4f} m  "
            f"success={metrics.get('success')}",
            flush=True,
        )

    mc_summary: dict[str, Any] | None = None
    n_trials = 0
    mc_trials: list[dict[str, Any]] = []
    plan = None

    run_dir = create_run_directory(output_root, cfg.study_id)
    write_yaml(run_dir / "study_config.yaml", cfg.model_dump())
    _write_reference_artifacts(run_dir, prepared)
    write_nominal_timeseries(
        run_dir,
        sim_result.t,
        sim_result.x,
        sim_result.u,
        x_hat=sim_result.x_hat,
    )
    write_json(run_dir / "nominal" / "metrics.json", metrics)
    ctrl_summary: dict[str, Any] = {
        "id": prepared.controller.id,
        "type": cfg.controller.type,
        "u_hover": prepared.controller.u_hover.tolist(),
        "design_vehicle_id": prepared.vehicle_nominal.vehicle_id,
        "mc_redesign_controller": bool(do_mc and cfg.monte_carlo.redesign_controller),
    }
    if isinstance(prepared.controller, LqrHoverController):
        ctrl_summary["K_shape"] = list(prepared.controller.k.shape)
        ctrl_summary["poles_real_max"] = float(np.max(np.real(prepared.controller.poles)))
    write_json(run_dir / "nominal" / "controller.json", ctrl_summary)
    write_controller_artifact(
        run_dir / "nominal" / "controller_artifact.yaml",
        controller_artifact_for(prepared.controller, prepared.vehicle_nominal),
    )

    if do_mc:
        n_trials = cfg.monte_carlo.n_trials
        mc_dir = run_dir / "monte_carlo"
        shards_root = mc_dir / "shards" if shards > 1 else None
        if progress:
            print(
                f"[uavsim] Monte Carlo  n_trials={n_trials}  "
                f"shards={shards}  redesign_controller="
                f"{cfg.monte_carlo.redesign_controller}  "
                f"(fixed K on nominal vehicle)",
                flush=True,
            )
        mc_trials, mc_summary, plan = run_mc_for_prepared(
            prepared,
            n_shards=shards,
            shards_root=shards_root,
            progress=progress,
        )
        if progress:
            print("[uavsim] Monte Carlo done", flush=True)
        write_merged_mc_artifacts(mc_dir, mc_trials, mc_summary, plan=plan if shards > 1 else None)
        # Keep single-shard path writing same layout as Phase 3
        if shards == 1:
            write_trials_csv(mc_dir / "trials.csv", mc_trials)
            write_trials_json(mc_dir / "trials.json", mc_trials)
            write_json(mc_dir / "summary.json", mc_summary)

    write_text_report(
        run_dir,
        metrics,
        cfg.study_id,
        mc_summary=mc_summary,
    )
    write_manifest(
        run_dir,
        study_id=cfg.study_id,
        seed=cfg.seed,
        config_hash=cfg_hash,
        execution_mode="sil",
        status="success" if overall_ok else "failed",
        extra={
            "vehicle_id": prepared.vehicle_nominal.vehicle_id,
            "vehicle_path": str(vehicle_path),
            "guidance_backend": prepared.reference.backend_id,
            "feasibility_ok": prepared.feasibility.ok,
            "n_trials": n_trials if do_mc else 0,
            "monte_carlo_enabled": bool(do_mc),
            "execution": {
                "mode": "local",
                "shards": shards if do_mc else 1,
                "backend": resolved_backend if do_mc else "nominal_only",
                "shard_plan": plan.to_dict() if plan is not None and shards > 1 else None,
            },
        },
    )

    return StudyRunResult(
        run_dir=run_dir,
        metrics=metrics,
        success=overall_ok,
        feasibility=prepared.feasibility.to_dict(),
        mc_summary=mc_summary,
        n_trials=n_trials if do_mc else 0,
        n_shards=shards if do_mc else 1,
        backend=resolved_backend if do_mc else "local",
    )


def run_study(
    study_path: str | Path,
    *,
    output_root: str | Path = "runs",
    force_mc: bool | None = None,
    n_trials_override: int | None = None,
    backend: BackendName | None = None,
    n_shards: int | None = None,
    docker_image: str | None = None,
    repo_root: Path | None = None,
    progress: bool = True,
) -> StudyRunResult:
    """CLI entry for ``uavsim study`` (MC when enabled in config)."""
    return run_nominal_study(
        study_path,
        output_root=output_root,
        run_mc=force_mc,
        n_trials_override=n_trials_override,
        backend=backend,
        n_shards=n_shards,
        docker_image=docker_image,
        repo_root=repo_root,
        progress=progress,
    )
