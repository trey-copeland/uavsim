"""Build controllers from config-like objects."""

from __future__ import annotations

from typing import Any  # noqa: I001 — used by _get defaults

import numpy as np

from uavsim.control.lqr import LqrHoverController, design_lqr_hover
from uavsim.control.ndi import NdiCascadeController, NdiGains, design_ndi_cascade
from uavsim.control.pid import PidCascadeController, PidGains, design_pid_cascade
from uavsim.vehicles.params import VehicleParams

AnyBuiltController = LqrHoverController | PidCascadeController | NdiCascadeController


def build_controller_from_mapping(cfg: Any, vehicle: VehicleParams) -> AnyBuiltController:
    """
    Build a controller from a pydantic model or mapping with a ``type`` field.

    Supported types: ``lqr_hover``, ``pid_cascade``, ``ndi_cascade``.
    """
    ctype = cfg["type"] if isinstance(cfg, dict) else cfg.type
    if ctype == "lqr_hover":
        q = cfg["Q_diag"] if isinstance(cfg, dict) else cfg.Q_diag
        r = cfg["R_diag"] if isinstance(cfg, dict) else cfg.R_diag
        return design_lqr_hover(
            vehicle,
            q_diag=np.asarray(q, dtype=float),
            r_diag=np.asarray(r, dtype=float),
            controller_id="lqr_hover",
        )
    if ctype == "pid_cascade":
        get = (
            (lambda k, d=None: cfg.get(k, d))
            if isinstance(cfg, dict)
            else (lambda k, d=None: getattr(cfg, k, d))
        )
        gains = PidGains(
            kp_pos=np.asarray(get("kp_pos"), dtype=float),
            kd_pos=np.asarray(get("kd_pos"), dtype=float),
            kp_att=np.asarray(get("kp_att"), dtype=float),
            kd_rate=np.asarray(get("kd_rate"), dtype=float),
        )
        max_tilt = get("max_tilt_rad", np.deg2rad(25.0))
        return design_pid_cascade(
            vehicle,
            gains=gains,
            controller_id="pid_cascade",
            max_tilt_rad=float(max_tilt),
        )
    if ctype == "ndi_cascade":
        get = (
            (lambda k, d=None: cfg.get(k, d))
            if isinstance(cfg, dict)
            else (lambda k, d=None: getattr(cfg, k, d))
        )
        gains = NdiGains(
            kp_pos=np.asarray(get("kp_pos"), dtype=float),
            kd_pos=np.asarray(get("kd_pos"), dtype=float),
            k_R=np.asarray(get("k_R"), dtype=float),
            k_omega=np.asarray(get("k_omega"), dtype=float),
        )
        max_tilt = get("max_tilt_rad", 0.7)
        invert_model = get("invert_model", "vacuum_rigid_body") or "vacuum_rigid_body"
        f_min_frac = get("f_min_frac_hover", 0.05)
        return design_ndi_cascade(
            vehicle,
            gains=gains,
            controller_id="ndi_cascade",
            max_tilt_rad=float(max_tilt),
            invert_model=str(invert_model),
            f_min_frac_hover=float(f_min_frac if f_min_frac is not None else 0.05),
        )
    msg = f"Unsupported controller type: {ctype!r}"
    raise ValueError(msg)


def controller_artifact_for(controller: Any, vehicle: VehicleParams) -> dict[str, Any]:
    from uavsim.control.export import (
        export_lqr_artifact,
        export_ndi_artifact,
        export_pid_artifact,
    )

    if isinstance(controller, LqrHoverController):
        return export_lqr_artifact(controller, vehicle=vehicle)
    if isinstance(controller, PidCascadeController):
        return export_pid_artifact(controller, vehicle=vehicle)
    if isinstance(controller, NdiCascadeController):
        return export_ndi_artifact(controller, vehicle=vehicle)
    msg = f"Cannot export controller type {type(controller)}"
    raise TypeError(msg)
