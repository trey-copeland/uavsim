"""Parametric vehicle perturbations for Monte Carlo trials."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from uavsim.vehicles.params import InertiaParams, VehicleParams


@dataclass(frozen=True)
class PerturbationSpec:
    """Relative Gaussian noise on mass / inertia / arm (heritage-inspired defaults)."""

    mass_rel_sigma: float = 0.05
    inertia_rel_sigma: float = 0.075
    arm_rel_sigma: float = 0.02
    min_mass_kg: float = 0.05
    min_inertia_kg_m2: float = 1e-6
    min_arm_m: float = 0.05


def trial_rng(base_seed: int, trial_id: int) -> np.random.Generator:
    """
    Deterministic RNG stream for trial ``trial_id``.

    Stream is a pure function of ``(base_seed, trial_id)`` so shards can
    reproduce any trial without coordinating other workers.
    """
    ss = np.random.SeedSequence([int(base_seed), int(trial_id)])
    return np.random.default_rng(ss)


def _positive_normal(
    rng: np.random.Generator, mean: float, rel_sigma: float, floor: float
) -> float:
    if rel_sigma <= 0:
        return float(mean)
    sample = float(rng.normal(mean, abs(mean) * rel_sigma))
    return max(sample, floor)


def perturb_vehicle(
    nominal: VehicleParams,
    *,
    base_seed: int,
    trial_id: int,
    spec: PerturbationSpec | None = None,
) -> tuple[VehicleParams, dict[str, float]]:
    """
    Draw a perturbed vehicle for trial ``trial_id``.

    Returns (vehicle, param_dict) where param_dict is flat for trial tables.
    """
    spec = spec or PerturbationSpec()
    rng = trial_rng(base_seed, trial_id)

    mass = _positive_normal(rng, nominal.mass_kg, spec.mass_rel_sigma, spec.min_mass_kg)
    ixx = _positive_normal(
        rng, nominal.inertia.ixx_kg_m2, spec.inertia_rel_sigma, spec.min_inertia_kg_m2
    )
    iyy = _positive_normal(
        rng, nominal.inertia.iyy_kg_m2, spec.inertia_rel_sigma, spec.min_inertia_kg_m2
    )
    izz = _positive_normal(
        rng, nominal.inertia.izz_kg_m2, spec.inertia_rel_sigma, spec.min_inertia_kg_m2
    )
    arm = _positive_normal(rng, nominal.arm_length_m, spec.arm_rel_sigma, spec.min_arm_m)

    # Scale thrust limit with mass so hover remains inside envelope
    thrust_scale = mass / nominal.mass_kg
    thrust_max = max(nominal.limits.thrust_max_n * thrust_scale, mass * nominal.gravity_m_s2 * 1.2)

    vehicle = nominal.model_copy(
        update={
            "mass_kg": mass,
            "arm_length_m": arm,
            "inertia": InertiaParams(ixx_kg_m2=ixx, iyy_kg_m2=iyy, izz_kg_m2=izz),
            "limits": nominal.limits.model_copy(update={"thrust_max_n": thrust_max}),
            "vehicle_id": f"{nominal.vehicle_id}_trial{trial_id}",
        }
    )
    params = {
        "mass_kg": mass,
        "ixx_kg_m2": ixx,
        "iyy_kg_m2": iyy,
        "izz_kg_m2": izz,
        "arm_length_m": arm,
        "thrust_max_n": thrust_max,
    }
    return vehicle, params
