"""Opt-in battery / energy bookkeeping (SIL power proxy)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from uavsim.vehicles.params import VehicleParams


@dataclass
class BatterySeries:
    """Time-aligned energy logs for export / metrics / demo UI."""

    power_w: np.ndarray
    soc: np.ndarray
    energy_wh_remaining: np.ndarray
    energy_used_wh: float
    energy_depleted: bool
    enabled: bool


def thrust_power_w(thrust_n: float, vehicle: VehicleParams) -> float:
    """Instantaneous electrical power proxy from commanded thrust."""
    bat = vehicle.battery
    if not bat.enabled:
        return 0.0
    hover = max(float(vehicle.hover_thrust_n()), 1e-9)
    ratio = max(float(thrust_n), 0.0) / hover
    return float(bat.idle_power_w + bat.hover_power_w * (ratio ** float(bat.thrust_power_exp)))


def integrate_battery(
    t: np.ndarray,
    u: np.ndarray,
    vehicle: VehicleParams,
) -> BatterySeries | None:
    """
    Trapezoidal energy integration along control history.

    Returns ``None`` when battery is disabled (callers skip keys / metrics).
    """
    bat = vehicle.battery
    if not bat.enabled:
        return None

    t = np.asarray(t, dtype=float).reshape(-1)
    u = np.asarray(u, dtype=float)
    if t.size == 0:
        return BatterySeries(
            power_w=np.zeros(0),
            soc=np.zeros(0),
            energy_wh_remaining=np.zeros(0),
            energy_used_wh=0.0,
            energy_depleted=False,
            enabled=True,
        )

    n = t.size
    thrust = u[:, 0] if u.ndim == 2 else np.full(n, float(u[0]))
    power = np.array([thrust_power_w(float(f), vehicle) for f in thrust], dtype=float)

    capacity = float(bat.capacity_wh)
    e0 = capacity * float(bat.initial_soc)
    energy = np.zeros(n, dtype=float)
    energy[0] = e0
    for i in range(n - 1):
        dt = float(t[i + 1] - t[i])
        if dt <= 0:
            energy[i + 1] = energy[i]
            continue
        # Average power over step → Wh
        p_avg = 0.5 * (power[i] + power[i + 1])
        de_wh = p_avg * dt / 3600.0
        energy[i + 1] = max(0.0, energy[i] - de_wh)

    soc = np.clip(energy / max(capacity, 1e-12), 0.0, 1.0)
    used = float(max(0.0, e0 - energy[-1]))
    depleted = bool(energy[-1] <= 1e-9 or np.any(energy <= 1e-9))
    return BatterySeries(
        power_w=power,
        soc=soc,
        energy_wh_remaining=energy,
        energy_used_wh=used,
        energy_depleted=depleted,
        enabled=True,
    )


def battery_metrics(series: BatterySeries | None) -> dict[str, float | bool]:
    if series is None or not series.enabled or series.soc.size == 0:
        return {}
    return {
        "soc_final": float(series.soc[-1]),
        "soc_min": float(np.min(series.soc)),
        "energy_used_wh": float(series.energy_used_wh),
        "energy_depleted": bool(series.energy_depleted),
        "peak_power_w": float(np.max(series.power_w)),
        "battery_enabled": True,
    }
