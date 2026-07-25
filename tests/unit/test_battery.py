"""Opt-in battery bookkeeping."""

from __future__ import annotations

import numpy as np

from uavsim.vehicles.battery import integrate_battery, thrust_power_w
from uavsim.vehicles.params import BatteryParams, default_vehicle


def test_disabled_battery_returns_none() -> None:
    v = default_vehicle()
    assert v.battery.enabled is False
    t = np.linspace(0.0, 1.0, 11)
    u = np.tile(v.u_hover(), (11, 1))
    assert integrate_battery(t, u, v) is None


def test_hover_scaled_drains_soc() -> None:
    v = default_vehicle()
    v = v.model_copy(
        update={
            "battery": BatteryParams(
                enabled=True,
                capacity_wh=1.0,
                initial_soc=1.0,
                hover_power_w=3600.0,  # 1 Wh/s at hover → empties in ~1 s
                idle_power_w=0.0,
                thrust_power_exp=1.0,
            )
        }
    )
    t = np.linspace(0.0, 2.0, 21)
    u = np.tile(v.u_hover(), (21, 1))
    series = integrate_battery(t, u, v)
    assert series is not None
    assert series.soc[0] == 1.0
    assert series.soc[-1] < 0.05
    assert series.energy_depleted is True
    assert series.energy_used_wh > 0.5
    assert thrust_power_w(float(v.hover_thrust_n()), v) == 3600.0


def test_old_yaml_without_battery_loads() -> None:
    from pathlib import Path

    from uavsim.vehicles.params import load_vehicle

    v = load_vehicle(Path("configs/vehicles/default_quadrotor.yaml"))
    assert v.battery.enabled is False
