"""Unit tests: MC perturbation, seed stability, summary schema."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from uavsim.monte_carlo import (
    PerturbationSpec,
    perturb_vehicle,
    read_trials_csv,
    run_monte_carlo,
    summarize_trials,
    trial_rng,
    write_trials_csv,
)
from uavsim.vehicles.params import default_vehicle


def test_trial_rng_deterministic() -> None:
    a = trial_rng(42, 3).normal(size=5)
    b = trial_rng(42, 3).normal(size=5)
    c = trial_rng(42, 4).normal(size=5)
    np.testing.assert_array_equal(a, b)
    assert not np.allclose(a, c)


def test_perturb_vehicle_changes_mass() -> None:
    nom = default_vehicle()
    v0, p0 = perturb_vehicle(nom, base_seed=1, trial_id=0)
    v1, p1 = perturb_vehicle(nom, base_seed=1, trial_id=1)
    assert v0.mass_kg > 0 and v1.mass_kg > 0
    # Same seed+id reproduces
    v0b, p0b = perturb_vehicle(nom, base_seed=1, trial_id=0)
    assert v0.mass_kg == v0b.mass_kg
    assert p0 == p0b
    # Different trials typically differ
    assert p0["mass_kg"] != p1["mass_kg"] or p0["ixx_kg_m2"] != p1["ixx_kg_m2"]


def test_perturb_respects_zero_sigma() -> None:
    nom = default_vehicle()
    spec = PerturbationSpec(
        mass_rel_sigma=0.0,
        inertia_rel_sigma=0.0,
        arm_rel_sigma=0.0,
        ct_rel_sigma=0.0,
        cq_rel_sigma=0.0,
        motor_tau_rel_sigma=0.0,
        omega_max_rel_sigma=0.0,
    )
    v, p = perturb_vehicle(nom, base_seed=0, trial_id=0, spec=spec)
    assert v.mass_kg == nom.mass_kg
    assert v.inertia.ixx_kg_m2 == nom.inertia.ixx_kg_m2
    assert v.propulsion.ct_n_s2 == nom.propulsion.ct_n_s2
    assert p["ct_n_s2"] == nom.propulsion.ct_n_s2
    assert p["omega_max_rad_s"] == nom.propulsion.omega_max_rad_s


def test_perturb_propulsion_when_sigma_set() -> None:
    nom = default_vehicle()
    spec = PerturbationSpec(
        mass_rel_sigma=0.0,
        inertia_rel_sigma=0.0,
        arm_rel_sigma=0.0,
        ct_rel_sigma=0.2,
        cq_rel_sigma=0.2,
        motor_tau_rel_sigma=0.25,
        omega_max_rel_sigma=0.15,
    )
    v0, p0 = perturb_vehicle(nom, base_seed=7, trial_id=0, spec=spec)
    v1, p1 = perturb_vehicle(nom, base_seed=7, trial_id=1, spec=spec)
    assert "ct_n_s2" in p0 and "omega_max_rad_s" in p0
    assert v0.propulsion.ct_n_s2 > 0
    assert v0.propulsion.omega_max_rad_s >= 50.0
    # Different trials differ on propulsion for large sigma
    assert (
        p0["ct_n_s2"] != p1["ct_n_s2"]
        or p0["motor_time_const_s"] != p1["motor_time_const_s"]
        or p0["omega_max_rad_s"] != p1["omega_max_rad_s"]
    )
    # Reproducible
    v0b, p0b = perturb_vehicle(nom, base_seed=7, trial_id=0, spec=spec)
    assert p0 == p0b


def test_run_monte_carlo_seed_stable() -> None:
    nom = default_vehicle()

    def trial_fn(trial_id: int, plant, params: dict[str, float]) -> dict:
        # Deterministic "metrics" from plant mass
        return {
            "rmse_position_m": plant.mass_kg,
            "max_position_error_m": params["ixx_kg_m2"],
            "success": True,
            "sim_success": True,
        }

    r1 = run_monte_carlo(
        nominal_vehicle=nom,
        base_seed=99,
        n_trials=3,
        trial_fn=trial_fn,
    )
    r2 = run_monte_carlo(
        nominal_vehicle=nom,
        base_seed=99,
        n_trials=3,
        trial_fn=trial_fn,
    )
    assert r1.trials == r2.trials
    assert r1.summary["n_trials"] == 3
    assert r1.summary["schema_version"] == 1
    assert "rmse_position_m" in r1.summary["metrics"]


def test_summarize_and_csv_roundtrip(tmp_path: Path) -> None:
    trials = [
        {
            "trial_id": 0,
            "mass_kg": 0.5,
            "rmse_position_m": 0.1,
            "success": True,
            "sim_success": True,
        },
        {
            "trial_id": 1,
            "mass_kg": 0.55,
            "rmse_position_m": 0.2,
            "success": False,
            "sim_success": True,
        },
    ]
    path = write_trials_csv(tmp_path / "trials.csv", trials)
    loaded = read_trials_csv(path)
    assert len(loaded) == 2
    assert loaded[0]["trial_id"] == 0
    assert loaded[1]["success"] is False

    summary = summarize_trials(trials)
    assert summary["n_success"] == 1
    assert abs(summary["failure_rate"] - 0.5) < 1e-12
