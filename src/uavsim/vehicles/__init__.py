"""Vehicle params, actuator limits, and config factories."""

from uavsim.vehicles.battery import BatterySeries, integrate_battery, thrust_power_w
from uavsim.vehicles.params import (
    AeroParams,
    BatteryParams,
    PropulsionParams,
    VehicleParams,
    default_vehicle,
    load_vehicle,
)

__all__ = [
    "AeroParams",
    "BatteryParams",
    "BatterySeries",
    "PropulsionParams",
    "VehicleParams",
    "default_vehicle",
    "integrate_battery",
    "load_vehicle",
    "thrust_power_w",
]
