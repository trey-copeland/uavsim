"""Versioned controller export / load (SIL round-trip; HIL handoff later)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from uavsim import __version__
from uavsim.control.lqr import LqrHoverController
from uavsim.control.pid import PidCascadeController
from uavsim.dynamics import CONTROL_DIM, STATE_DIM
from uavsim.vehicles.params import VehicleParams, load_vehicle

ARTIFACT_SCHEMA_VERSION = 1


def export_lqr_artifact(
    controller: LqrHoverController,
    *,
    vehicle: VehicleParams | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    vehicle = vehicle or controller.vehicle
    art: dict[str, Any] = {
        "schema_version": ARTIFACT_SCHEMA_VERSION,
        "controller_type": "lqr_hover",
        "controller_id": controller.id,
        "created_at": datetime.now(UTC).isoformat(),
        "uavsim_version": __version__,
        "frames": {
            "state": "NED_FRD_12",
            "control": "thrust_Nm_body",
            "state_order": [
                "x",
                "y",
                "z",
                "phi",
                "theta",
                "psi",
                "vx",
                "vy",
                "vz",
                "p",
                "q",
                "r",
            ],
            "control_order": ["F", "tau_phi", "tau_theta", "tau_psi"],
        },
        "vehicle_id": vehicle.vehicle_id,
        "vehicle": {
            "mass_kg": vehicle.mass_kg,
            "gravity_m_s2": vehicle.gravity_m_s2,
            "arm_length_m": vehicle.arm_length_m,
            "inertia": vehicle.inertia.model_dump(),
            "limits": vehicle.limits.model_dump(),
        },
        "trim": {
            "u_hover": controller.u_hover.tolist(),
            "x_eq": [0.0] * STATE_DIM,
        },
        "gains": {
            "K": np.asarray(controller.k, dtype=float).tolist(),
            "Q_diag": np.diag(controller.q).tolist(),
            "R_diag": np.diag(controller.r).tolist(),
        },
        "design": {
            "poles_real": np.real(controller.poles).tolist(),
            "poles_imag": np.imag(controller.poles).tolist(),
        },
    }
    if extra:
        art["extra"] = extra
    return art


def export_pid_artifact(
    controller: PidCascadeController,
    *,
    vehicle: VehicleParams | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    vehicle = vehicle or controller.vehicle
    art: dict[str, Any] = {
        "schema_version": ARTIFACT_SCHEMA_VERSION,
        "controller_type": "pid_cascade",
        "controller_id": controller.id,
        "created_at": datetime.now(UTC).isoformat(),
        "uavsim_version": __version__,
        "frames": {
            "state": "NED_FRD_12",
            "control": "thrust_Nm_body",
        },
        "vehicle_id": vehicle.vehicle_id,
        "vehicle": {
            "mass_kg": vehicle.mass_kg,
            "gravity_m_s2": vehicle.gravity_m_s2,
            "arm_length_m": vehicle.arm_length_m,
            "inertia": vehicle.inertia.model_dump(),
            "limits": vehicle.limits.model_dump(),
        },
        "trim": {"u_hover": controller.u_hover.tolist()},
        "gains": controller.gains_dict(),
    }
    if extra:
        art["extra"] = extra
    return art


def write_controller_artifact(path: Path, artifact: dict[str, Any]) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(artifact, f, sort_keys=False)
    return path


def load_controller_artifact(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        msg = f"Controller artifact must be a mapping: {path}"
        raise ValueError(msg)
    if int(data.get("schema_version", -1)) != ARTIFACT_SCHEMA_VERSION:
        msg = (
            f"Unsupported controller artifact schema_version="
            f"{data.get('schema_version')}; expected {ARTIFACT_SCHEMA_VERSION}"
        )
        raise ValueError(msg)
    return data


def controller_from_artifact(
    artifact: dict[str, Any],
    *,
    vehicle: VehicleParams | None = None,
) -> LqrHoverController | PidCascadeController:
    """Rebuild an in-process controller from a versioned artifact (SIL round-trip)."""
    if vehicle is None:
        vdata = artifact.get("vehicle")
        if not isinstance(vdata, dict):
            msg = "Artifact missing vehicle block and no vehicle provided"
            raise ValueError(msg)
        from uavsim.vehicles.params import ActuatorLimits, InertiaParams

        vehicle = VehicleParams(
            vehicle_id=str(artifact.get("vehicle_id", "from_artifact")),
            mass_kg=float(vdata["mass_kg"]),
            gravity_m_s2=float(vdata.get("gravity_m_s2", 9.81)),
            arm_length_m=float(vdata["arm_length_m"]),
            inertia=InertiaParams(**vdata["inertia"]),
            limits=ActuatorLimits(**vdata["limits"]),
        )

    ctype = artifact.get("controller_type")
    if ctype == "lqr_hover":
        gains = artifact["gains"]
        k = np.asarray(gains["K"], dtype=float)
        if k.shape != (CONTROL_DIM, STATE_DIM):
            msg = f"LQR K must be shape ({CONTROL_DIM}, {STATE_DIM}), got {k.shape}"
            raise ValueError(msg)
        q_diag = np.asarray(gains.get("Q_diag", np.ones(STATE_DIM)), dtype=float)
        r_diag = np.asarray(gains.get("R_diag", np.ones(CONTROL_DIM)), dtype=float)
        poles = np.asarray(artifact.get("design", {}).get("poles_real", []), dtype=float)
        if poles.size == 0:
            poles = np.full(STATE_DIM, -1.0)
        return LqrHoverController(
            id=str(artifact.get("controller_id", "lqr_hover")),
            vehicle=vehicle,
            k=k,
            q=np.diag(q_diag),
            r=np.diag(r_diag),
            poles=poles.astype(complex),
        )
    if ctype == "pid_cascade":
        from uavsim.control.pid import PidGains, design_pid_cascade

        g = artifact["gains"]
        gains = PidGains(
            kp_pos=np.asarray(g["kp_pos"], dtype=float),
            kd_pos=np.asarray(g["kd_pos"], dtype=float),
            kp_att=np.asarray(g["kp_att"], dtype=float),
            kd_rate=np.asarray(g["kd_rate"], dtype=float),
        )
        return design_pid_cascade(
            vehicle,
            gains=gains,
            controller_id=str(artifact.get("controller_id", "pid_cascade")),
        )
    msg = f"Unknown controller_type in artifact: {ctype!r}"
    raise ValueError(msg)


def export_from_run_dir(run_dir: str | Path, out_path: str | Path) -> Path:
    """
    Export controller artifact from a completed run directory.

    Prefers ``nominal/controller_artifact.yaml`` if present; otherwise errors
    with a clear message (older runs without Phase 5 artifacts).
    """
    run_dir = Path(run_dir)
    src = run_dir / "nominal" / "controller_artifact.yaml"
    if not src.is_file():
        msg = (
            f"No controller artifact in run dir: {src}\n"
            "Re-run the study with a Phase 5+ build, or pass a design artifact path."
        )
        raise FileNotFoundError(msg)
    art = load_controller_artifact(src)
    return write_controller_artifact(Path(out_path), art)


def export_from_vehicle_design(
    vehicle_path: str | Path,
    *,
    controller_type: str = "lqr_hover",
    out_path: str | Path,
    q_diag: list[float] | None = None,
    r_diag: list[float] | None = None,
) -> Path:
    """Design-on-the-spot export without a prior run (LQR only helper)."""
    from uavsim.control.lqr import design_lqr_hover

    vehicle = load_vehicle(vehicle_path)
    if controller_type != "lqr_hover":
        msg = "export_from_vehicle_design currently supports lqr_hover only"
        raise ValueError(msg)
    ctrl = design_lqr_hover(
        vehicle,
        q_diag=None if q_diag is None else np.asarray(q_diag, dtype=float),
        r_diag=None if r_diag is None else np.asarray(r_diag, dtype=float),
    )
    art = export_lqr_artifact(ctrl, vehicle=vehicle)
    return write_controller_artifact(Path(out_path), art)
