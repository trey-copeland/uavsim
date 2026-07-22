"""Aerodynamic aids: body drag, lumped prop H-force, ground effect (D-4/D-5).

All effects are **opt-in** via :class:`~uavsim.vehicles.params.AeroParams`.
Defaults leave the rigid-body plant bit-identical to the no-aero model.
"""

from __future__ import annotations

import numpy as np

from uavsim.vehicles.params import AeroParams, VehicleParams

# Numerical floor so Cheeseman–Bennett does not blow up at h→0
_H_AGL_FLOOR_M = 1e-3
_KAPPA_MAX = 3.0


def height_agl_m(z_ned_m: float, ground_z_ned_m: float) -> float:
    """
    Height above flat ground in NED (z positive down).

    ``h = ground_z - z``; vehicle above ground when ``z < ground_z``.
    """
    return float(ground_z_ned_m - z_ned_m)


def ground_effect_kappa(
    h_agl_m: float,
    *,
    rotor_radius_m: float,
    model: str,
    ge_exp_a: float,
    ge_exp_b: float,
    kappa_max: float = _KAPPA_MAX,
) -> float:
    """
    Thrust multiplier κ(h) from ground effect (κ ≥ 1 near ground, → 1 far away).

    Models
    ------
    * ``none`` — 1.0
    * ``cheeseman`` — Cheeseman–Bennett style
      ``κ = 1 / (1 - (R/(4h))²)`` for ``h > R/4``, else clamped
    * ``exp`` — ``κ = 1 + a·exp(-b·h/R)``
    """
    if model == "none" or rotor_radius_m <= 0.0:
        return 1.0

    h = max(float(h_agl_m), _H_AGL_FLOOR_M)
    r = float(rotor_radius_m)

    if model == "cheeseman":
        # Singularity at h = R/4; stay above with a small margin
        h_safe = max(h, 0.26 * r)
        ratio = r / (4.0 * h_safe)
        denom = 1.0 - ratio * ratio
        kappa = kappa_max if denom <= 1e-6 else 1.0 / denom
    elif model == "exp":
        kappa = 1.0 + float(ge_exp_a) * float(np.exp(-float(ge_exp_b) * h / r))
    else:
        msg = f"unknown ground_effect model {model!r}"
        raise ValueError(msg)

    return float(min(max(kappa, 1.0), kappa_max))


def body_drag_force_ned(
    v_ned: np.ndarray,
    aero: AeroParams,
) -> np.ndarray:
    """Translational drag in NED: ``-b_lin v - b_quad ||v|| v``."""
    v = np.asarray(v_ned, dtype=float).reshape(3)
    f = np.zeros(3)
    bl = float(aero.drag_lin_ns_m)
    bq = float(aero.drag_quad_ns2_m2)
    if bl != 0.0:
        f -= bl * v
    if bq != 0.0:
        speed = float(np.linalg.norm(v))
        f -= bq * speed * v
    return f


def prop_h_force_body(
    v_body: np.ndarray,
    thrust_n: float,
    aero: AeroParams,
) -> np.ndarray:
    """
    Lumped rotor-plane (H) force in **body** frame.

    ``f_xy = -k_h · T · v_xy``, ``f_z = 0``.  ``k_h`` has units s/m.
    Captures advance-ratio drag opposing freestream in the disk plane without
    full BEMT. Zero when ``prop_h_s_per_m == 0`` or thrust is zero.
    """
    k = float(aero.prop_h_s_per_m)
    if k == 0.0 or thrust_n == 0.0:
        return np.zeros(3)
    vb = np.asarray(v_body, dtype=float).reshape(3)
    f = np.zeros(3)
    f[0] = -k * float(thrust_n) * vb[0]
    f[1] = -k * float(thrust_n) * vb[1]
    return f


def rate_damping_torque(omega_body: np.ndarray, aero: AeroParams) -> np.ndarray:
    """Linear rate damping ``τ = -c · ω`` (body frame)."""
    c = float(aero.rate_damp_nm_s)
    if c == 0.0:
        return np.zeros(3)
    return -c * np.asarray(omega_body, dtype=float).reshape(3)


def apply_aero(
    *,
    z_ned_m: float,
    v_ned: np.ndarray,
    omega_body: np.ndarray,
    r_b2i: np.ndarray,
    thrust_n: float,
    tau_body: np.ndarray,
    vehicle: VehicleParams,
) -> tuple[float, np.ndarray, np.ndarray, float]:
    """
    Apply ground effect, body drag, prop H-force, and rate damping.

    Parameters
    ----------
    thrust_n, tau_body
        Commanded / realized body wrench (pre-aero).
    r_b2i
        Body→inertial (NED) rotation matrix.

    Returns
    -------
    thrust_eff, f_extra_ned, tau_eff, kappa
        Effective thrust (GE), extra NED force (drag + H), damped torque, κ.
    """
    aero = vehicle.aero
    v = np.asarray(v_ned, dtype=float).reshape(3)
    omega = np.asarray(omega_body, dtype=float).reshape(3)
    tau = np.asarray(tau_body, dtype=float).reshape(3)
    r = np.asarray(r_b2i, dtype=float).reshape(3, 3)

    h = height_agl_m(z_ned_m, aero.ground_z_ned_m)
    kappa = ground_effect_kappa(
        h,
        rotor_radius_m=aero.rotor_radius_m,
        model=aero.ground_effect,
        ge_exp_a=aero.ge_exp_a,
        ge_exp_b=aero.ge_exp_b,
        kappa_max=aero.ge_kappa_max,
    )
    thrust_eff = float(thrust_n) * kappa

    f_drag = body_drag_force_ned(v, aero)
    # Body velocity for H-force: v_b = R^T v_i
    v_body = r.T @ v
    f_h_body = prop_h_force_body(v_body, thrust_eff, aero)
    f_h_ned = r @ f_h_body
    f_extra = f_drag + f_h_ned

    tau_eff = tau + rate_damping_torque(omega, aero)
    return thrust_eff, f_extra, tau_eff, kappa
