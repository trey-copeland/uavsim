"""Body drag, prop H-force, and ground effect (D-4/D-5)."""

from __future__ import annotations

import numpy as np
import pytest

from uavsim.dynamics import (
    body_drag_force_ned,
    ground_effect_kappa,
    height_agl_m,
    hover_linearization,
    prop_h_force_body,
    state_derivative,
    state_derivative_quat,
)
from uavsim.vehicles import AeroParams, default_vehicle
from uavsim.vehicles.params import load_vehicle


def test_default_aero_is_off() -> None:
    v = default_vehicle()
    assert v.aero.drag_lin_ns_m == 0.0
    assert v.aero.prop_h_s_per_m == 0.0
    assert v.aero.ground_effect == "none"


def test_default_hover_trim_unchanged() -> None:
    vehicle = default_vehicle()
    x = np.zeros(12)
    u = vehicle.u_hover()
    x_dot = state_derivative(x, u, vehicle)
    assert np.linalg.norm(x_dot) < 1e-10


def test_body_drag_opposes_velocity() -> None:
    aero = AeroParams(drag_lin_ns_m=0.1, drag_quad_ns2_m2=0.05)
    v = np.array([1.0, 0.0, 0.0])
    f = body_drag_force_ned(v, aero)
    assert f[0] < 0.0
    np.testing.assert_allclose(f[1:], 0.0)


def test_prop_h_in_body_xy_only() -> None:
    aero = AeroParams(prop_h_s_per_m=0.1)
    vb = np.array([2.0, -1.0, 3.0])
    f = prop_h_force_body(vb, thrust_n=5.0, aero=aero)
    assert f[0] < 0.0 and f[1] > 0.0
    assert f[2] == 0.0


def test_linear_drag_dissipates_kinetic_energy() -> None:
    """Open-loop hover wrench + initial velocity: drag slows the vehicle."""
    vehicle = default_vehicle().model_copy(update={"aero": AeroParams(drag_lin_ns_m=0.5)})
    x = np.zeros(12)
    x[6] = 2.0  # north velocity
    u = vehicle.u_hover()
    x_dot = state_derivative(x, u, vehicle)
    # a_x = F_drag / m = -0.5 * 2 / 0.5 = -2
    np.testing.assert_allclose(x_dot[6], -2.0, atol=1e-12)
    # kinetic power v·(m a) < 0
    assert float(np.dot(x[6:9], x_dot[6:9])) < 0.0


def test_ground_effect_kappa_cheeseman_near_ground() -> None:
    # Cheeseman is mild until h ≲ R; use h/R ≈ 0.4 for a clear boost
    kappa_far = ground_effect_kappa(
        5.0, rotor_radius_m=0.12, model="cheeseman", ge_exp_a=0.5, ge_exp_b=2.0
    )
    kappa_near = ground_effect_kappa(
        0.05, rotor_radius_m=0.12, model="cheeseman", ge_exp_a=0.5, ge_exp_b=2.0
    )
    assert kappa_far < 1.05
    assert kappa_near > 1.4
    assert kappa_near <= 3.0


def test_ground_effect_boosts_vertical_accel() -> None:
    """Same thrust command near ground → larger upward accel (NED −z)."""
    base = default_vehicle()
    vehicle = base.model_copy(
        update={
            "aero": AeroParams(
                ground_effect="cheeseman",
                rotor_radius_m=0.12,
                ground_z_ned_m=2.0,
            )
        }
    )
    u = base.u_hover()
    x_far = np.zeros(12)
    x_far[2] = 0.0  # AGL = 2.0
    x_near = np.zeros(12)
    x_near[2] = 1.95  # AGL = 0.05
    a_far = state_derivative(x_far, u, vehicle)[8]
    a_near = state_derivative(x_near, u, vehicle)[8]
    # NED +z down: extra thrust → more negative vertical accel
    assert a_near < a_far - 0.5


def test_hover_with_ge_not_trimmed_at_mg() -> None:
    """With κ>1, u=mg gives residual accel at low AGL (teaching mismatch)."""
    vehicle = default_vehicle().model_copy(
        update={
            "aero": AeroParams(
                ground_effect="cheeseman",
                rotor_radius_m=0.12,
                ground_z_ned_m=1.05,
            )
        }
    )
    x = np.zeros(12)
    x[2] = 1.0  # AGL = 0.05
    x_dot = state_derivative(x, vehicle.u_hover(), vehicle)
    assert abs(x_dot[8]) > 0.1


def test_height_agl_ned() -> None:
    assert height_agl_m(1.0, 1.2) == pytest.approx(0.2)
    assert height_agl_m(1.5, 1.2) == pytest.approx(-0.3)


def test_quat_path_matches_euler_with_aero() -> None:
    vehicle = default_vehicle().model_copy(
        update={
            "aero": AeroParams(
                drag_lin_ns_m=0.1,
                drag_quad_ns2_m2=0.05,
                prop_h_s_per_m=0.05,
                rate_damp_nm_s=0.001,
            )
        }
    )
    x_e = np.zeros(12)
    x_e[3:6] = [0.05, -0.03, 0.1]
    x_e[6:9] = [0.5, -0.2, 0.1]
    x_e[9:12] = [0.1, -0.05, 0.02]
    from uavsim.dynamics import euler_state_to_quat_state

    x_q = euler_state_to_quat_state(x_e)
    u = vehicle.u_hover() * 1.05
    u[1] = 0.01
    de = state_derivative(x_e, u, vehicle)
    dq = state_derivative_quat(x_q, u, vehicle)
    np.testing.assert_allclose(de[0:3], dq[0:3], atol=1e-12)
    np.testing.assert_allclose(de[6:9], dq[7:10], atol=1e-12)
    np.testing.assert_allclose(de[9:12], dq[10:13], atol=1e-12)


def test_linearization_includes_linear_drag() -> None:
    vehicle = default_vehicle().model_copy(
        update={"aero": AeroParams(drag_lin_ns_m=0.2, rate_damp_nm_s=0.01)}
    )
    a, _b = hover_linearization(vehicle)
    m = vehicle.mass_kg
    np.testing.assert_allclose(a[6, 6], -0.2 / m)
    np.testing.assert_allclose(a[9, 9], -0.01 / vehicle.inertia.ixx_kg_m2)


def test_load_aero_vehicle_yaml() -> None:
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    v = load_vehicle(root / "configs/vehicles/default_quadrotor_aero.yaml")
    assert v.aero.drag_lin_ns_m > 0
    assert v.aero.prop_h_s_per_m > 0
    v_ge = load_vehicle(root / "configs/vehicles/default_quadrotor_ge.yaml")
    assert v_ge.aero.ground_effect == "cheeseman"
