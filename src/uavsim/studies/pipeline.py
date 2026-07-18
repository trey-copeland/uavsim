"""Nominal + Monte Carlo study pipeline: config → plan → sim → metrics → run dir."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from uavsim.control import design_lqr_hover
from uavsim.control.lqr import LqrHoverController
from uavsim.guidance import HoldGuidance, WaypointsGuidance
from uavsim.metrics import compute_metrics
from uavsim.monte_carlo import (
    run_monte_carlo,
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


@dataclass
class StudyRunResult:
    run_dir: Path
    metrics: dict[str, Any]
    success: bool
    feasibility: dict[str, Any] | None = None
    mc_summary: dict[str, Any] | None = None
    n_trials: int = 0


@dataclass
class PreparedStudy:
    cfg: StudyConfig
    vehicle_nominal: VehicleParams
    vehicle_path: Path
    cfg_hash: str
    controller: LqrHoverController
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
    controller = design_lqr_hover(
        vehicle,
        q_diag=np.asarray(cfg.controller.Q_diag, dtype=float),
        r_diag=np.asarray(cfg.controller.R_diag, dtype=float),
        controller_id=cfg.controller.type,
    )
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
    controller: LqrHoverController | None = None,
) -> tuple[ClosedLoopResult, dict[str, Any]]:
    """Simulate one closed-loop run; returns (sim_result, metrics)."""
    ctrl = controller if controller is not None else prepared.controller
    cfg = prepared.cfg
    plant = SimPlant(plant_vehicle)
    adapter = InProcessControllerAdapter(ctrl, prepared.reference)
    sim_result = simulate_closed_loop(
        plant,
        adapter,
        t0=prepared.reference.t0,
        tf=prepared.reference.tf,
        x0=prepared.x0,
        max_step=cfg.sim.dt_s,
        rtol=cfg.sim.rtol,
        atol=cfg.sim.atol,
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


def run_nominal_study(
    study_path: str | Path,
    *,
    output_root: str | Path = "runs",
    run_mc: bool | None = None,
    n_trials_override: int | None = None,
) -> StudyRunResult:
    """
    Run nominal SIL study (+ optional MC if config enables it).

    ``run_mc``: None → follow config; True/False force enable/disable MC.
    ``n_trials_override``: if set, overrides ``monte_carlo.n_trials``.
    """
    cfg, vehicle_path, cfg_hash, _mission_path = load_study(study_path)
    if n_trials_override is not None:
        if n_trials_override < 1:
            msg = "n_trials_override must be >= 1"
            raise ValueError(msg)
        cfg.monte_carlo.n_trials = n_trials_override
    prepared = prepare_study(cfg, vehicle_path, cfg_hash)

    sim_result, metrics = run_closed_loop_trial(prepared, prepared.vehicle_nominal)
    metrics["feasibility_ok"] = prepared.feasibility.ok
    overall_ok = bool(sim_result.success and metrics.get("success", False))

    do_mc = cfg.monte_carlo.enabled if run_mc is None else run_mc
    if do_mc and cfg.monte_carlo.backend != "local":
        msg = f"MC backend {cfg.monte_carlo.backend!r} not implemented (Phase 4 for docker)"
        raise NotImplementedError(msg)
    if do_mc and cfg.monte_carlo.shards != 1:
        msg = "Local MC with shards>1 is Phase 4; use shards: 1 for Phase 3"
        raise NotImplementedError(msg)

    mc_summary: dict[str, Any] | None = None
    n_trials = 0
    mc_trials: list[dict[str, Any]] = []

    if do_mc:
        mc_cfg = cfg.monte_carlo
        n_trials = mc_cfg.n_trials
        redesign = mc_cfg.redesign_controller
        q = np.asarray(cfg.controller.Q_diag, dtype=float)
        r = np.asarray(cfg.controller.R_diag, dtype=float)

        def trial_fn(
            trial_id: int,
            plant_vehicle: VehicleParams,
            _params: dict[str, float],
        ) -> dict[str, Any]:
            if redesign:
                ctrl = design_lqr_hover(
                    plant_vehicle,
                    q_diag=q,
                    r_diag=r,
                    controller_id=cfg.controller.type,
                )
            else:
                ctrl = prepared.controller
            _sim, m = run_closed_loop_trial(prepared, plant_vehicle, controller=ctrl)
            return _metric_row(m)

        mc_result = run_monte_carlo(
            nominal_vehicle=prepared.vehicle_nominal,
            base_seed=cfg.seed,
            n_trials=n_trials,
            trial_fn=trial_fn,
            spec=mc_cfg.perturbation_spec(),
            redesign_controller=redesign,
        )
        mc_trials = mc_result.trials
        mc_summary = mc_result.summary

    run_dir = create_run_directory(output_root, cfg.study_id)
    write_yaml(run_dir / "study_config.yaml", cfg.model_dump())
    _write_reference_artifacts(run_dir, prepared)
    write_nominal_timeseries(run_dir, sim_result.t, sim_result.x, sim_result.u)
    write_json(run_dir / "nominal" / "metrics.json", metrics)
    write_json(
        run_dir / "nominal" / "controller.json",
        {
            "id": prepared.controller.id,
            "K_shape": list(prepared.controller.k.shape),
            "poles_real_max": float(np.max(np.real(prepared.controller.poles))),
            "u_hover": prepared.controller.u_hover.tolist(),
            "design_vehicle_id": prepared.vehicle_nominal.vehicle_id,
            "mc_redesign_controller": bool(do_mc and cfg.monte_carlo.redesign_controller),
        },
    )

    if do_mc and mc_summary is not None:
        mc_dir = run_dir / "monte_carlo"
        mc_dir.mkdir(exist_ok=True)
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
                "shards": 1,
                "backend": "local" if do_mc else "nominal_only",
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
    )


def run_study(
    study_path: str | Path,
    *,
    output_root: str | Path = "runs",
    force_mc: bool | None = None,
    n_trials_override: int | None = None,
) -> StudyRunResult:
    """CLI entry for ``uavsim study`` (MC when enabled in config)."""
    return run_nominal_study(
        study_path,
        output_root=output_root,
        run_mc=force_mc,
        n_trials_override=n_trials_override,
    )
