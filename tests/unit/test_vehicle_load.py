"""Vehicle config loading."""

from __future__ import annotations

from pathlib import Path

from uavsim.vehicles import load_vehicle

ROOT = Path(__file__).resolve().parents[2]


def test_load_default_vehicle_yaml() -> None:
    path = ROOT / "configs" / "vehicles" / "default_quadrotor.yaml"
    v = load_vehicle(path)
    assert v.mass_kg == 0.5
    assert v.vehicle_id == "default_quadrotor"
    assert v.limits.thrust_max_n > v.hover_thrust_n()
