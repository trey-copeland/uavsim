"""PID cascade position/attitude controller (second core law for comparisons)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from uavsim.control.base import saturate
from uavsim.interfaces import ActuatorCommand, MeasurementBus
from uavsim.reference import ReferenceSample
from uavsim.vehicles.params import VehicleParams


@dataclass
class PidGains:
    """Diagonal gains for outer position and inner attitude loops."""

    kp_pos: np.ndarray  # (3,)
    kd_pos: np.ndarray  # (3,)
    kp_att: np.ndarray  # (3,) roll, pitch, yaw
    kd_rate: np.ndarray  # (3,) p, q, r

    def __post_init__(self) -> None:
        self.kp_pos = np.asarray(self.kp_pos, dtype=float).reshape(3)
        self.kd_pos = np.asarray(self.kd_pos, dtype=float).reshape(3)
        self.kp_att = np.asarray(self.kp_att, dtype=float).reshape(3)
        self.kd_rate = np.asarray(self.kd_rate, dtype=float).reshape(3)


# Tuned for 500 g class hover / gentle tracking demos
DEFAULT_PID_GAINS = PidGains(
    kp_pos=np.array([2.5, 2.5, 6.0]),
    kd_pos=np.array([2.0, 2.0, 3.5]),
    kp_att=np.array([8.0, 8.0, 2.0]),
    kd_rate=np.array([0.8, 0.8, 0.4]),
)


@dataclass
class PidCascadeController:
    """
    Cascaded PD: position → accel → tilt/thrust; attitude → body torques.

    Underactuated NED approximation (small-angle feedforward tilt). Suitable as
    a non-LQR baseline for comparison studies — not a full geometric tracker.
    """

    id: str
    vehicle: VehicleParams
    gains: PidGains
    max_tilt_rad: float = np.deg2rad(25.0)

    @property
    def u_hover(self) -> np.ndarray:
        return self.vehicle.u_hover()

    def gains_dict(self) -> dict[str, list[float]]:
        g = self.gains
        return {
            "kp_pos": g.kp_pos.tolist(),
            "kd_pos": g.kd_pos.tolist(),
            "kp_att": g.kp_att.tolist(),
            "kd_rate": g.kd_rate.tolist(),
            "max_tilt_rad": float(self.max_tilt_rad),
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

        pos = x[0:3]
        vel = x[6:9]
        euler = x[3:6]
        omega = x[9:12]
        pos_ref = x_ref[0:3]
        vel_ref = x_ref[6:9]
        # Optional reference attitude (from feedforward trajectory)
        euler_ref_traj = x_ref[3:6]

        e_pos = pos_ref - pos
        e_vel = vel_ref - vel
        a_cmd = gains.kp_pos * e_pos + gains.kd_pos * e_vel

        # NED: z positive down. Hover F = m g. Vertical PD on down-accel.
        # zddot ≈ g - F/m  (level)  ⇒  F = m (g - a_z_cmd)
        f_cmd = m * (g - a_cmd[2])
        f_cmd = float(
            np.clip(f_cmd, self.vehicle.limits.thrust_min_n, self.vehicle.limits.thrust_max_n)
        )

        # Horizontal accel → tilt (matches plant: +θ → −ẍ, +φ → +ÿ at hover thrust)
        ax, ay = float(a_cmd[0]), float(a_cmd[1])
        smax = float(np.sin(self.max_tilt_rad))
        theta_des = float(np.clip(-ax / g, -smax, smax))
        phi_des = float(np.clip(ay / g, -smax, smax))
        # Prefer trajectory feedforward attitude when present (waypoint refs)
        if np.linalg.norm(euler_ref_traj[0:2]) > 1e-6:
            phi_des = 0.5 * phi_des + 0.5 * float(euler_ref_traj[0])
            theta_des = 0.5 * theta_des + 0.5 * float(euler_ref_traj[1])
        psi_des = float(euler_ref_traj[2])

        e_att = np.array([phi_des, theta_des, psi_des], dtype=float) - euler
        # wrap yaw error roughly
        e_att[2] = (e_att[2] + np.pi) % (2 * np.pi) - np.pi
        tau = gains.kp_att * e_att - gains.kd_rate * omega

        u = np.array([f_cmd, tau[0], tau[1], tau[2]], dtype=float)
        u = saturate(u, self.vehicle.limits.u_min(), self.vehicle.limits.u_max())
        return ActuatorCommand(u=u)


def design_pid_cascade(
    vehicle: VehicleParams,
    gains: PidGains | None = None,
    *,
    controller_id: str = "pid_cascade",
    max_tilt_rad: float | None = None,
) -> PidCascadeController:
    g = gains or DEFAULT_PID_GAINS
    return PidCascadeController(
        id=controller_id,
        vehicle=vehicle,
        gains=g,
        max_tilt_rad=float(max_tilt_rad) if max_tilt_rad is not None else np.deg2rad(25.0),
    )
