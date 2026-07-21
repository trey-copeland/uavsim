"""Build observers from study config."""

from __future__ import annotations

from typing import Any

from uavsim.estimation.identity import IdentityObserver
from uavsim.estimation.linear_kf import LinearStateKalmanFilter
from uavsim.estimation.measurements import MeasurementModel
from uavsim.vehicles.params import VehicleParams


def build_observer(
    observer_cfg: Any,
    vehicle: VehicleParams,
) -> tuple[Any, MeasurementModel | None]:
    """
    Returns ``(observer, measurement_model)``.

    ``observer_cfg`` is ``None``, a string type name, or an object/dict with fields.
    """
    if observer_cfg is None:
        return IdentityObserver(), None

    if isinstance(observer_cfg, str):
        otype = observer_cfg
        params: dict[str, Any] = {}
    elif hasattr(observer_cfg, "type"):
        otype = str(observer_cfg.type)
        params = {
            "seed": getattr(observer_cfg, "seed", 0),
            "pos_sigma_m": getattr(observer_cfg, "pos_sigma_m", 0.05),
            "vel_sigma_m_s": getattr(observer_cfg, "vel_sigma_m_s", 0.05),
            "att_sigma_rad": getattr(observer_cfg, "att_sigma_rad", 0.02),
            "omega_sigma_rad_s": getattr(observer_cfg, "omega_sigma_rad_s", 0.05),
            "process_sigma": getattr(observer_cfg, "process_sigma", 0.02),
        }
    elif isinstance(observer_cfg, dict):
        otype = str(observer_cfg.get("type", "none"))
        params = dict(observer_cfg)
    else:
        msg = f"Unsupported observer config: {type(observer_cfg)}"
        raise TypeError(msg)

    if otype in ("none", "identity", ""):
        return IdentityObserver(), None

    if otype == "linear_kf":
        meas = MeasurementModel(
            seed=int(params.get("seed", 0)),
            pos_sigma_m=float(params.get("pos_sigma_m", 0.05)),
            vel_sigma_m_s=float(params.get("vel_sigma_m_s", 0.05)),
            att_sigma_rad=float(params.get("att_sigma_rad", 0.02)),
            omega_sigma_rad_s=float(params.get("omega_sigma_rad_s", 0.05)),
        )
        kf = LinearStateKalmanFilter(
            vehicle,
            pos_sigma_m=float(params.get("pos_sigma_m", 0.05)),
            vel_sigma_m_s=float(params.get("vel_sigma_m_s", 0.05)),
            att_sigma_rad=float(params.get("att_sigma_rad", 0.02)),
            omega_sigma_rad_s=float(params.get("omega_sigma_rad_s", 0.05)),
            process_sigma=float(params.get("process_sigma", 0.02)),
        )
        return kf, meas

    msg = f"Unknown observer type {otype!r}"
    raise ValueError(msg)
