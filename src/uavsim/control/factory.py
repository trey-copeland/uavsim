"""Build controllers from config-like objects."""

from __future__ import annotations

from typing import Any  # noqa: I001 — used by _get defaults

import numpy as np

from uavsim.control.lqr import LqrHoverController, design_lqr_hover
from uavsim.control.pid import PidCascadeController, PidGains, design_pid_cascade
from uavsim.vehicles.params import VehicleParams


def build_controller_from_mapping(
    cfg: Any, vehicle: VehicleParams
) -> LqrHoverController | PidCascadeController:
    """
    Build a controller from a pydantic model or mapping with a ``type`` field.

    Supported types: ``lqr_hover``, ``pid_cascade``.
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
    msg = f"Unsupported controller type: {ctype!r}"
    raise ValueError(msg)


def controller_artifact_for(controller: Any, vehicle: VehicleParams) -> dict[str, Any]:
    from uavsim.control.export import export_lqr_artifact, export_pid_artifact

    if isinstance(controller, LqrHoverController):
        return export_lqr_artifact(controller, vehicle=vehicle)
    if isinstance(controller, PidCascadeController):
        return export_pid_artifact(controller, vehicle=vehicle)
    msg = f"Cannot export controller type {type(controller)}"
    raise TypeError(msg)
