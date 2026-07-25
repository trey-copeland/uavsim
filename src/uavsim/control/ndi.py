"""Nonlinear dynamic inversion cascade (position PD + SO(3)/rate NDI).

Inverts the vacuum rigid-body model to body wrench ``u = [F, τ]``.
Plant frames: NED inertial, FRD body; thrust along **−body-z**.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from uavsim.control.base import saturate
from uavsim.dynamics.attitude_error import rotation_error_vector_from_dcm
from uavsim.dynamics.rotations import rotation_body_to_inertial
from uavsim.interfaces import ActuatorCommand, MeasurementBus
from uavsim.reference import ReferenceSample
from uavsim.vehicles.params import VehicleParams


@dataclass
class NdiGains:
    """Diagonal gains for outer position PD and inner SO(3)/rate NDI."""

    kp_pos: np.ndarray  # (3,)
    kd_pos: np.ndarray  # (3,)
    k_R: np.ndarray  # (3,) attitude (SO(3) error)
    k_omega: np.ndarray  # (3,) body-rate

    def __post_init__(self) -> None:
        self.kp_pos = np.asarray(self.kp_pos, dtype=float).reshape(3)
        self.kd_pos = np.asarray(self.kd_pos, dtype=float).reshape(3)
        self.k_R = np.asarray(self.k_R, dtype=float).reshape(3)
        self.k_omega = np.asarray(self.k_omega, dtype=float).reshape(3)


# Memoryless (RK45-safe). k_R / k_omega are **torque-space** gains (like PID),
# applied via α_des = −I⁻¹ (K_R e_R + K_ω e_ω) so τ = ω×Iω − K_R e_R − K_ω e_ω.
DEFAULT_NDI_GAINS = NdiGains(
    kp_pos=np.array([4.0, 4.0, 9.0]),
    kd_pos=np.array([3.0, 3.0, 5.0]),
    k_R=np.array([12.0, 12.0, 3.0]),
    k_omega=np.array([1.2, 1.2, 0.5]),
)


def desired_rotation_from_thrust_and_yaw(f_thrust_i: np.ndarray, yaw: float) -> np.ndarray:
    """
    Build ``R_b2i`` so inertial thrust ``f_thrust_i = −F · b₃`` and yaw about vertical.

    ``b₃`` is the body-z axis in NED (third column of ``R``). At hover,
    ``f_thrust_i ≈ [0, 0, −mg]`` ⇒ ``b₃ ≈ [0, 0, 1]``.
    """
    f = np.asarray(f_thrust_i, dtype=float).reshape(3)
    n = float(np.linalg.norm(f))
    b3 = np.array([0.0, 0.0, 1.0]) if n < 1e-9 else -f / n

    c, s = float(np.cos(yaw)), float(np.sin(yaw))
    b1_c = np.array([c, s, 0.0])
    b2 = np.cross(b3, b1_c)
    n2 = float(np.linalg.norm(b2))
    if n2 < 1e-8:
        # b3 nearly parallel to heading plane vector — use lateral fallback
        b1_c = np.array([-s, c, 0.0])
        b2 = np.cross(b3, b1_c)
        n2 = float(np.linalg.norm(b2))
        if n2 < 1e-8:
            b2 = np.array([0.0, 1.0, 0.0])
            n2 = 1.0
    b2 = b2 / n2
    b1 = np.cross(b2, b3)
    n1 = float(np.linalg.norm(b1))
    b1 = np.array([1.0, 0.0, 0.0]) if n1 < 1e-15 else b1 / n1
    # Re-orthogonalize b3 in case of numerical drift
    b3 = np.cross(b1, b2)
    n3 = float(np.linalg.norm(b3))
    if n3 > 1e-15:
        b3 = b3 / n3
    return np.column_stack([b1, b2, b3])


@dataclass
class NdiCascadeController:
    """
    Cascade NDI: position PD → thrust direction + collective; SO(3)/rate NDI → τ.

    Inversion model (v1): vacuum rigid body (diagonal ``I``, mass ``m``, gravity ``g``).
    No aero or motor dynamics in the inverse — plant may still include them.

    Memoryless (safe under SciPy RK45, which re-enters the controller at
    intermediate times). ``ω_des ≈ 0``; keep ``k_omega`` modest so rate damping
    does not fight a moving ``R_des``.
    """

    id: str
    vehicle: VehicleParams
    gains: NdiGains
    max_tilt_rad: float = 0.7
    invert_model: str = "vacuum_rigid_body"
    # Floor as fraction of hover thrust when limits.thrust_min is 0
    f_min_frac_hover: float = 0.05

    @property
    def u_hover(self) -> np.ndarray:
        return self.vehicle.u_hover()

    def gains_dict(self) -> dict[str, list[float] | float | str]:
        g = self.gains
        return {
            "kp_pos": g.kp_pos.tolist(),
            "kd_pos": g.kd_pos.tolist(),
            "k_R": g.k_R.tolist(),
            "k_omega": g.k_omega.tolist(),
            "max_tilt_rad": float(self.max_tilt_rad),
            "invert_model": self.invert_model,
            "f_min_frac_hover": float(self.f_min_frac_hover),
        }

    def compute(
        self,
        t: float,
        measurements: MeasurementBus,
        reference: ReferenceSample,
    ) -> ActuatorCommand:
        _ = t
        x = measurements.x
        x_ref = reference.x_ref
        m = self.vehicle.mass_kg
        g = self.vehicle.gravity_m_s2
        gains = self.gains
        inertia = self.vehicle.inertia.as_diag()

        pos = x[0:3]
        vel = x[6:9]
        euler = x[3:6]
        omega = x[9:12]
        pos_ref = x_ref[0:3]
        vel_ref = x_ref[6:9]
        euler_ref = x_ref[3:6]
        psi_des = float(euler_ref[2])

        e_pos = pos_ref - pos
        e_vel = vel_ref - vel
        # Virtual control: desired inertial acceleration (NED). a_r ≈ 0 in v1.
        a_des = gains.kp_pos * e_pos + gains.kd_pos * e_vel

        # Clamp horizontal accel so commanded tilt stays within max_tilt_rad
        a_max = g * float(np.sin(self.max_tilt_rad))
        ax, ay = float(a_des[0]), float(a_des[1])
        horiz = float(np.hypot(ax, ay))
        if horiz > a_max > 0.0:
            scale = a_max / horiz
            ax *= scale
            ay *= scale
        a_des = np.array([ax, ay, float(a_des[2])], dtype=float)

        # Plant: a = (R @ [0,0,-F] + m g e_z) / m
        # ⇒ f_thrust_i = R @ [0,0,-F] = m (a_des − g e_z)
        g_vec = np.array([0.0, 0.0, g], dtype=float)
        f_thrust_i = m * (a_des - g_vec)

        f_mag = float(np.linalg.norm(f_thrust_i))
        f_hover = m * g
        f_floor = max(float(self.vehicle.limits.thrust_min_n), self.f_min_frac_hover * f_hover)
        f_cmd = float(np.clip(f_mag, f_floor, float(self.vehicle.limits.thrust_max_n)))
        # Rebuild direction at saturated magnitude for attitude ref consistency
        if f_mag > 1e-12:
            f_thrust_i = f_thrust_i * (f_cmd / f_mag)
        else:
            f_thrust_i = np.array([0.0, 0.0, -f_cmd], dtype=float)

        r_des = desired_rotation_from_thrust_and_yaw(f_thrust_i, psi_des)
        r = rotation_body_to_inertial(float(euler[0]), float(euler[1]), float(euler[2]))

        # e_R = vee(log(R_desᵀ R)); ω_des ≈ 0 (memoryless / RK45-safe)
        # Torque-space gains: α_des = −I⁻¹ (K_R e_R + K_ω e_ω)
        e_R = rotation_error_vector_from_dcm(r, r_des)
        e_omega = omega
        torque_pd = gains.k_R * e_R + gains.k_omega * e_omega
        alpha_des = -np.linalg.solve(inertia, torque_pd)

        # Euler inverse: τ = ω × (I ω) + I α_des = ω×Iω − K_R e_R − K_ω e_ω
        i_omega = inertia @ omega
        tau = np.cross(omega, i_omega) + inertia @ alpha_des

        u = np.array([f_cmd, float(tau[0]), float(tau[1]), float(tau[2])], dtype=float)
        u = saturate(u, self.vehicle.limits.u_min(), self.vehicle.limits.u_max())
        return ActuatorCommand(u=u)


def design_ndi_cascade(
    vehicle: VehicleParams,
    gains: NdiGains | None = None,
    *,
    controller_id: str = "ndi_cascade",
    max_tilt_rad: float | None = None,
    invert_model: str = "vacuum_rigid_body",
    f_min_frac_hover: float = 0.05,
) -> NdiCascadeController:
    g = gains or DEFAULT_NDI_GAINS
    return NdiCascadeController(
        id=controller_id,
        vehicle=vehicle,
        gains=g,
        max_tilt_rad=float(max_tilt_rad) if max_tilt_rad is not None else 0.7,
        invert_model=invert_model,
        f_min_frac_hover=float(f_min_frac_hover),
    )
