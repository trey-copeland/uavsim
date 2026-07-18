"""Nominal study pipeline: config → plan → sim → metrics → run dir."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from uavsim.control import design_lqr_hover
from uavsim.metrics import compute_metrics
from uavsim.reference import hold_at_ned
from uavsim.results import (
    create_run_directory,
    write_json,
    write_manifest,
    write_nominal_timeseries,
    write_text_report,
    write_yaml,
)
from uavsim.sim import InProcessControllerAdapter, SimPlant, simulate_closed_loop
from uavsim.studies.config import StudyConfig, load_study
from uavsim.vehicles.params import load_vehicle


@dataclass
class StudyRunResult:
    run_dir: Path
    metrics: dict[str, Any]
    success: bool


def run_nominal_study(
    study_path: str | Path,
    *,
    output_root: str | Path = "runs",
) -> StudyRunResult:
    cfg, vehicle_path, cfg_hash = load_study(study_path)
    vehicle = load_vehicle(vehicle_path)

    controller = design_lqr_hover(
        vehicle,
        q_diag=np.asarray(cfg.controller.Q_diag, dtype=float),
        r_diag=np.asarray(cfg.controller.R_diag, dtype=float),
        controller_id=cfg.controller.type,
    )

    g = cfg.guidance
    reference = hold_at_ned(
        position_ned_m=np.asarray(g.position_ned_m, dtype=float),
        yaw_rad=g.yaw_rad,
        duration_s=g.duration_s,
    )

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
    overall_ok = bool(sim_result.success and metrics.get("success", False))

    run_dir = create_run_directory(output_root, cfg.study_id)
    write_yaml(run_dir / "study_config.yaml", cfg.model_dump())
    write_yaml(
        run_dir / "guidance" / "backend.yaml",
        {
            "backend_id": reference.backend_id,
            "metadata": reference.metadata,
            "t0": reference.t0,
            "tf": reference.tf,
        },
    )
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
        extra={"vehicle_id": vehicle.vehicle_id, "vehicle_path": str(vehicle_path)},
    )

    return StudyRunResult(run_dir=run_dir, metrics=metrics, success=overall_ok)


def run_study_from_config(cfg: StudyConfig, vehicle_path: Path, **kwargs: Any) -> StudyRunResult:
    """Test helper: write cfg to temp is avoided; use path-based API in production."""
    _ = cfg
    _ = vehicle_path
    raise NotImplementedError("Use run_nominal_study(path)")
