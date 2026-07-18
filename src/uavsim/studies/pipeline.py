"""Nominal study pipeline: config → plan → sim → metrics → run dir."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from uavsim.control import design_lqr_hover
from uavsim.guidance import HoldGuidance, WaypointsGuidance
from uavsim.metrics import compute_metrics
from uavsim.reference import SampledReference
from uavsim.results import (
    create_run_directory,
    write_json,
    write_manifest,
    write_nominal_timeseries,
    write_text_report,
    write_yaml,
)
from uavsim.sim import InProcessControllerAdapter, SimPlant, simulate_closed_loop
from uavsim.studies.config import (
    HoldGuidanceConfig,
    StudyConfig,
    WaypointsGuidanceConfig,
    guidance_mission_dict,
    load_study,
)
from uavsim.vehicles.params import load_vehicle


@dataclass
class StudyRunResult:
    run_dir: Path
    metrics: dict[str, Any]
    success: bool
    feasibility: dict[str, Any] | None = None


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


def run_nominal_study(
    study_path: str | Path,
    *,
    output_root: str | Path = "runs",
) -> StudyRunResult:
    cfg, vehicle_path, cfg_hash, _mission_path = load_study(study_path)
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
    feasibility = plan.feasibility

    if cfg.initial_state is not None:
        x0 = cfg.initial_state.to_array()
    else:
        x0 = reference.evaluate(reference.t0).x_ref.copy()

    plant = SimPlant(vehicle)
    adapter = InProcessControllerAdapter(controller, reference)
    sim_result = simulate_closed_loop(
        plant,
        adapter,
        t0=reference.t0,
        tf=reference.tf,
        x0=x0,
        max_step=cfg.sim.dt_s,
        rtol=cfg.sim.rtol,
        atol=cfg.sim.atol,
    )

    metrics = compute_metrics(
        sim_result.t,
        sim_result.x,
        sim_result.u,
        reference,
        position_bound_m=cfg.metrics.position_bound_m,
    )
    metrics["sim_success"] = sim_result.success
    metrics["sim_message"] = sim_result.message
    metrics["feasibility_ok"] = feasibility.ok
    overall_ok = bool(sim_result.success and metrics.get("success", False))

    run_dir = create_run_directory(output_root, cfg.study_id)
    write_yaml(run_dir / "study_config.yaml", cfg.model_dump())
    write_yaml(
        run_dir / "guidance" / "backend.yaml",
        {
            "backend_id": reference.backend_id,
            "metadata": reference.metadata,
            "diagnostics": plan.diagnostics,
            "t0": reference.t0,
            "tf": reference.tf,
        },
    )
    write_json(run_dir / "guidance" / "feasibility.json", feasibility.to_dict())

    # Reference artifact: hold or sampled grid summary
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

    write_nominal_timeseries(run_dir, sim_result.t, sim_result.x, sim_result.u)
    write_json(run_dir / "nominal" / "metrics.json", metrics)
    write_json(
        run_dir / "nominal" / "controller.json",
        {
            "id": controller.id,
            "K_shape": list(controller.k.shape),
            "poles_real_max": float(np.max(np.real(controller.poles))),
            "u_hover": controller.u_hover.tolist(),
        },
    )
    write_text_report(run_dir, metrics, cfg.study_id)
    write_manifest(
        run_dir,
        study_id=cfg.study_id,
        seed=cfg.seed,
        config_hash=cfg_hash,
        execution_mode="sil",
        status="success" if overall_ok else "failed",
        extra={
            "vehicle_id": vehicle.vehicle_id,
            "vehicle_path": str(vehicle_path),
            "guidance_backend": reference.backend_id,
            "feasibility_ok": feasibility.ok,
        },
    )

    return StudyRunResult(
        run_dir=run_dir,
        metrics=metrics,
        success=overall_ok,
        feasibility=feasibility.to_dict(),
    )
