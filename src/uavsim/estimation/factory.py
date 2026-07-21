"""Build observers from study config."""

from __future__ import annotations

from typing import Any

from uavsim.estimation.channels import normalize_channels
from uavsim.estimation.identity import IdentityObserver
from uavsim.estimation.linear_kf import LinearStateKalmanFilter
from uavsim.estimation.measurements import MeasurementModel
from uavsim.estimation.mekf import ErrorStateMekf
from uavsim.vehicles.params import VehicleParams


def _params_from_cfg(observer_cfg: Any) -> tuple[str, dict[str, Any]]:
    if observer_cfg is None:
        return "none", {}
    if isinstance(observer_cfg, str):
        return observer_cfg, {}
    if hasattr(observer_cfg, "type"):
        return str(observer_cfg.type), {
            "seed": getattr(observer_cfg, "seed", 0),
            "pos_sigma_m": getattr(observer_cfg, "pos_sigma_m", 0.05),
            "vel_sigma_m_s": getattr(observer_cfg, "vel_sigma_m_s", 0.05),
            "att_sigma_rad": getattr(observer_cfg, "att_sigma_rad", 0.02),
            "omega_sigma_rad_s": getattr(observer_cfg, "omega_sigma_rad_s", 0.05),
            "process_sigma": getattr(observer_cfg, "process_sigma", 0.02),
            "channels": getattr(observer_cfg, "channels", None),
        }
    if isinstance(observer_cfg, dict):
        return str(observer_cfg.get("type", "none")), dict(observer_cfg)
    msg = f"Unsupported observer config: {type(observer_cfg)}"
    raise TypeError(msg)


def build_observer(
    observer_cfg: Any,
    vehicle: VehicleParams,
) -> tuple[Any, MeasurementModel | None]:
    """Returns ``(observer, measurement_model)``."""
    otype, params = _params_from_cfg(observer_cfg)
    if otype in ("none", "identity", ""):
        return IdentityObserver(), None

    channels = params.get("channels")
    if channels is not None:
        channels = normalize_channels(channels)

    common = {
        "pos_sigma_m": float(params.get("pos_sigma_m", 0.05)),
        "vel_sigma_m_s": float(params.get("vel_sigma_m_s", 0.05)),
        "att_sigma_rad": float(params.get("att_sigma_rad", 0.02)),
        "omega_sigma_rad_s": float(params.get("omega_sigma_rad_s", 0.05)),
        "process_sigma": float(params.get("process_sigma", 0.02)),
        "channels": channels,
    }
    from uavsim.estimation.channels import DEFAULT_CHANNELS

    ch_list = list(channels) if channels else list(DEFAULT_CHANNELS)
    common["channels"] = ch_list
    meas = MeasurementModel(
        seed=int(params.get("seed", 0)),
        pos_sigma_m=common["pos_sigma_m"],
        vel_sigma_m_s=common["vel_sigma_m_s"],
        att_sigma_rad=common["att_sigma_rad"],
        omega_sigma_rad_s=common["omega_sigma_rad_s"],
        channels=ch_list,
    )

    if otype == "linear_kf":
        kf = LinearStateKalmanFilter(vehicle, **common)
        return kf, meas

    if otype == "mekf":
        filt = ErrorStateMekf(vehicle, **common)
        return filt, meas

    msg = f"Unknown observer type {otype!r}"
    raise ValueError(msg)
