"""Cascade NDI unit tests (signs, hover, inversion, tilt safety, saturation)."""

from __future__ import annotations

import numpy as np

from uavsim.control import design_ndi_cascade
from uavsim.control.export import export_ndi_artifact
from uavsim.control.ndi import (
    clip_virtual_accel_for_tilt,
    commanded_tilt_rad_from_accel,
    desired_rotation_from_thrust_and_yaw,
)
from uavsim.dynamics.rotations import rotation_body_to_inertial
from uavsim.interfaces import MeasurementBus
from uavsim.reference import ReferenceSample
from uavsim.vehicles.params import default_vehicle


def test_ndi_hover_command_near_mg() -> None:
    vehicle = default_vehicle()
    ctrl = design_ndi_cascade(vehicle)
    x = np.zeros(12)
    ref = ReferenceSample(t=0.0, x_ref=np.zeros(12))
    bus = MeasurementBus(t=0.0, x=x)
    u = ctrl.compute(0.0, bus, ref).u
    assert abs(u[0] - vehicle.hover_thrust_n()) < 0.5
    assert np.linalg.norm(u[1:4]) < 0.5


def test_ndi_pushes_toward_reference_north() -> None:
    """North of target → need −ẍ (south) → −θ plant map → +pitch torque initially."""
    vehicle = default_vehicle()
    ctrl = design_ndi_cascade(vehicle)
    x = np.zeros(12)
    x[0] = 1.0  # north of target
    ref = ReferenceSample(t=0.0, x_ref=np.zeros(12))
    bus = MeasurementBus(t=0.0, x=x)
    u = ctrl.compute(0.0, bus, ref).u
    assert np.isfinite(u).all()
    # a_des_x < 0 ⇒ f_x < 0 ⇒ b3_x > 0 ⇒ θ_des > 0 at hover; +pitch torque
    assert u[2] > 0.0


def test_ndi_altitude_and_east_signs() -> None:
    vehicle = default_vehicle()
    ctrl = design_ndi_cascade(vehicle)
    ref = ReferenceSample(t=0.0, x_ref=np.zeros(12))

    # Too deep (NED +z): need upward accel (−z) ⇒ more thrust
    x_z = np.zeros(12)
    x_z[2] = 1.0
    u_z = ctrl.compute(0.0, MeasurementBus(t=0.0, x=x_z), ref).u
    assert u_z[0] > vehicle.hover_thrust_n()

    # East of target → −ÿ demand → −φ_des → negative roll torque initially
    x_e = np.zeros(12)
    x_e[1] = 1.0
    u_e = ctrl.compute(0.0, MeasurementBus(t=0.0, x=x_e), ref).u
    assert u_e[1] < 0.0


def test_ndi_attitude_error_zero_torque_at_aligned_hover() -> None:
    """At hover with matched attitude and ω=0, τ ≈ 0 and F ≈ mg."""
    vehicle = default_vehicle()
    ctrl = design_ndi_cascade(vehicle)
    x = np.zeros(12)
    ref = ReferenceSample(t=0.0, x_ref=np.zeros(12))
    u = ctrl.compute(0.0, MeasurementBus(t=0.0, x=x), ref).u
    np.testing.assert_allclose(u[1:4], 0.0, atol=1e-9)
    np.testing.assert_allclose(u[0], vehicle.hover_thrust_n(), atol=1e-6)


def test_ndi_inversion_identity_nonzero_rate() -> None:
    """
    With e_R≈0 and prescribed ω, torque matches Euler inverse:
    τ = ω×Iω − K_ω ω  (torque-space gains; ω_des=0).
    """
    vehicle = default_vehicle()
    ctrl = design_ndi_cascade(vehicle)
    omega = np.array([0.2, -0.1, 0.05])
    x = np.zeros(12)
    x[9:12] = omega
    ref = ReferenceSample(t=0.0, x_ref=np.zeros(12))
    u = ctrl.compute(0.0, MeasurementBus(t=0.0, x=x), ref).u

    i = vehicle.inertia.as_diag()
    tau_expected = np.cross(omega, i @ omega) - ctrl.gains.k_omega * omega
    np.testing.assert_allclose(u[1:4], tau_expected, rtol=1e-5, atol=1e-4)


def test_ndi_factory_default_gains_match_yaml_shape() -> None:
    vehicle = default_vehicle()
    ctrl = design_ndi_cascade(vehicle)
    g = ctrl.gains_dict()
    assert len(g["kp_pos"]) == 3
    assert len(g["k_R"]) == 3


def test_ndi_thrust_floor_and_saturation() -> None:
    vehicle = default_vehicle()
    ctrl = design_ndi_cascade(vehicle)
    # Huge down accel demand (NED +z) would drive F→0 without floor
    x = np.zeros(12)
    x[2] = -50.0  # far above target → want to fall hard
    ref = ReferenceSample(t=0.0, x_ref=np.zeros(12))
    u = ctrl.compute(0.0, MeasurementBus(t=0.0, x=x), ref).u
    f_floor = ctrl.f_min_frac_hover * vehicle.hover_thrust_n()
    assert u[0] >= f_floor - 1e-9
    assert u[0] <= vehicle.limits.thrust_max_n + 1e-9
    assert np.all(np.abs(u[1:4]) <= vehicle.limits.torque_max_nm + 1e-9)


def test_clip_virtual_accel_prevents_inverted_thrust() -> None:
    """Large positive a_z alone would flip f_z; clip keeps upright cone."""
    g = 9.81
    max_tilt = 0.7
    a_raw = np.array([2.0, 0.0, 20.0])  # a_z ≫ g
    a_clip = clip_virtual_accel_for_tilt(a_raw, g, max_tilt)
    assert a_clip[2] < g
    tilt = commanded_tilt_rad_from_accel(a_clip, g)
    assert tilt <= max_tilt + 1e-9
    # Combined horizontal + vertical demand that previously commanded ~172°
    a_hard = np.array([-40.0, 0.0, 54.0])  # ~10 m north, ~6 m above at high gains
    a_safe = clip_virtual_accel_for_tilt(a_hard, g, max_tilt)
    assert commanded_tilt_rad_from_accel(a_safe, g) <= max_tilt + 1e-9


def test_ndi_max_tilt_bounds_commanded_attitude() -> None:
    """
    Combined lateral + vertical error must not invert R_des.

    Regression for Finding 1: horizontal-only clamp left a_z free and could
    command ~170° tilt despite max_tilt_rad ≈ 0.7.
    """
    vehicle = default_vehicle()
    max_tilt = 0.7
    ctrl = design_ndi_cascade(vehicle, max_tilt_rad=max_tilt)
    x = np.zeros(12)
    x[0] = 10.0  # north of target
    x[2] = -6.0  # above target (NED z+ down)
    ref = ReferenceSample(t=0.0, x_ref=np.zeros(12))
    # Reconstruct a_des the controller would use after clamp via gains
    e_pos = -x[0:3]
    a_des = ctrl.gains.kp_pos * e_pos  # vel error 0
    a_clip = clip_virtual_accel_for_tilt(a_des, vehicle.gravity_m_s2, max_tilt)
    tilt = commanded_tilt_rad_from_accel(a_clip, vehicle.gravity_m_s2)
    assert tilt <= max_tilt + 1e-6, f"commanded tilt {tilt} > max {max_tilt}"

    # Closed-loop command still finite and F ≥ floor
    u = ctrl.compute(0.0, MeasurementBus(t=0.0, x=x), ref).u
    assert np.isfinite(u).all()
    f_i = vehicle.mass_kg * (a_clip - np.array([0.0, 0.0, vehicle.gravity_m_s2]))
    r_des = desired_rotation_from_thrust_and_yaw(f_i, 0.0)
    b3_z = float(r_des[2, 2])
    assert b3_z >= float(np.cos(max_tilt)) - 1e-6
    assert b3_z > 0.0  # upper hemisphere


def test_desired_rotation_hover_and_north_accel() -> None:
    m, g = 0.5, 9.81
    # Hover force
    f_h = np.array([0.0, 0.0, -m * g])
    r = desired_rotation_from_thrust_and_yaw(f_h, yaw=0.0)
    np.testing.assert_allclose(r[:, 2], [0.0, 0.0, 1.0], atol=1e-9)
    # North accel: f_i = m([ax,0,0] - [0,0,g])
    ax = 2.0
    f = m * np.array([ax, 0.0, -g])
    r2 = desired_rotation_from_thrust_and_yaw(f, yaw=0.0)
    # b3_x < 0 for +ax (plant: +θ → −ẍ ⇒ need −θ for +ẍ)
    assert r2[0, 2] < 0.0
    # R should be proper
    assert abs(np.linalg.det(r2) - 1.0) < 1e-9


def test_desired_rotation_nonzero_yaw() -> None:
    """Heading column follows yaw; R remains proper SO(3)."""
    m, g = 0.5, 9.81
    f = np.array([0.0, 0.0, -m * g])
    yaw = np.deg2rad(35.0)
    r = desired_rotation_from_thrust_and_yaw(f, yaw=yaw)
    np.testing.assert_allclose(r[:, 2], [0.0, 0.0, 1.0], atol=1e-9)
    # body-x projects onto horizontal heading
    b1_h = r[0:2, 0]
    b1_h = b1_h / (np.linalg.norm(b1_h) + 1e-15)
    expect = np.array([np.cos(yaw), np.sin(yaw)])
    np.testing.assert_allclose(b1_h, expect, atol=1e-9)
    assert abs(np.linalg.det(r) - 1.0) < 1e-9
    np.testing.assert_allclose(r.T @ r, np.eye(3), atol=1e-9)


def test_desired_rotation_near_horizontal_heading_fallback() -> None:
    """Degenerate branch when b3 nearly parallel to nominal heading vector."""
    # Nearly horizontal b3 along +x (would make cross with b1_c ~0 at yaw=0)
    f = np.array([-1.0, 0.0, -1e-9])  # b3 ≈ +x
    r = desired_rotation_from_thrust_and_yaw(f, yaw=0.0)
    assert abs(np.linalg.det(r) - 1.0) < 1e-6
    np.testing.assert_allclose(r.T @ r, np.eye(3), atol=1e-6)


def test_ndi_export_round_trip() -> None:
    from uavsim.control import controller_from_artifact

    vehicle = default_vehicle()
    ctrl = design_ndi_cascade(vehicle)
    art = export_ndi_artifact(ctrl, vehicle=vehicle)
    assert art["controller_type"] == "ndi_cascade"
    assert art["design"]["invert_model"] == "vacuum_rigid_body"
    loaded = controller_from_artifact(art)
    assert loaded.id == "ndi_cascade"
    x = np.zeros(12)
    x[0] = 0.3
    ref = ReferenceSample(t=0.0, x_ref=np.zeros(12))
    bus = MeasurementBus(t=0.0, x=x)
    u1 = ctrl.compute(0.0, bus, ref).u
    u2 = loaded.compute(0.0, bus, ref).u
    np.testing.assert_allclose(u1, u2)


def test_ndi_factory_from_mapping() -> None:
    from uavsim.control import build_controller_from_mapping

    vehicle = default_vehicle()
    cfg = {
        "type": "ndi_cascade",
        "kp_pos": [4.0, 4.0, 9.0],
        "kd_pos": [3.0, 3.0, 5.5],
        "k_R": [12.0, 12.0, 3.0],
        "k_omega": [1.2, 1.2, 0.5],
        "max_tilt_rad": 0.7,
    }
    ctrl = build_controller_from_mapping(cfg, vehicle)
    assert ctrl.id == "ndi_cascade"
    u = ctrl.compute(
        0.0, MeasurementBus(t=0.0, x=np.zeros(12)), ReferenceSample(t=0.0, x_ref=np.zeros(12))
    ).u
    assert u.shape == (4,)


def test_ndi_so3_matches_dcm_path() -> None:
    """Sanity: level R_des vs small roll produces restoring roll torque."""
    vehicle = default_vehicle()
    ctrl = design_ndi_cascade(vehicle)
    x = np.zeros(12)
    x[3] = 0.15  # +φ
    ref = ReferenceSample(t=0.0, x_ref=np.zeros(12))
    u = ctrl.compute(0.0, MeasurementBus(t=0.0, x=x), ref).u
    assert u[1] < 0.0  # restore toward level
    # DCM identity check
    r = rotation_body_to_inertial(0.15, 0.0, 0.0)
    assert abs(np.linalg.det(r) - 1.0) < 1e-9
