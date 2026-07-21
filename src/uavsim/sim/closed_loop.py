"""Closed-loop integration using plant + command source (+ optional observer)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.integrate import solve_ivp

from uavsim.dynamics import CONTROL_DIM, STATE_DIM
from uavsim.estimation.identity import IdentityObserver
from uavsim.estimation.measurements import MeasurementModel
from uavsim.interfaces import MeasurementBus
from uavsim.sim.adapters import CommandSource
from uavsim.sim.plant import SimPlant


@dataclass
class ClosedLoopResult:
    t: np.ndarray  # (N,)
    x: np.ndarray  # (N, 12) true Euler layout for metrics/export
    u: np.ndarray  # (N, 4)
    success: bool
    message: str
    attitude: str = "euler"
    x_hat: np.ndarray | None = None  # (N, 12) estimates when observer active
    observer_id: str = "none"


def simulate_closed_loop(
    plant: SimPlant,
    command_source: CommandSource,
    *,
    t0: float,
    tf: float,
    x0: np.ndarray,
    max_step: float = 0.02,
    rtol: float = 1e-6,
    atol: float = 1e-8,
    observer=None,
    measurement_model: MeasurementModel | None = None,
) -> ClosedLoopResult:
    """Integrate nonlinear plant under a command source on [t0, tf].

    - Euler plant + identity observer: SciPy RK45 (legacy path).
    - Quaternion plant and/or non-identity observer: fixed-step RK4 with
      optional measurement noise and Kalman (or other) updates.
    Output ``x`` is always **true** Euler 12-state for metrics.
    """
    plant.reset(x0, t0=t0)
    obs = observer if observer is not None else IdentityObserver()
    obs.reset(plant.x_euler(), t0=t0)

    use_fixed = plant.dynamics.attitude == "quat" or not isinstance(obs, IdentityObserver)
    if use_fixed:
        return _simulate_fixed_step(
            plant,
            command_source,
            t0=t0,
            tf=tf,
            max_step=max_step,
            observer=obs,
            measurement_model=measurement_model,
        )
    return _simulate_euler_ivp(
        plant,
        command_source,
        t0=t0,
        tf=tf,
        x0=x0,
        max_step=max_step,
        rtol=rtol,
        atol=atol,
    )


def _simulate_euler_ivp(
    plant: SimPlant,
    command_source: CommandSource,
    *,
    t0: float,
    tf: float,
    x0: np.ndarray,
    max_step: float,
    rtol: float,
    atol: float,
) -> ClosedLoopResult:
    def rhs(t: float, x: np.ndarray) -> np.ndarray:
        meas = MeasurementBus(t=t, x=x)
        cmd = command_source.command(t, meas)
        u = plant.apply_command(cmd)
        return plant.derivatives(t, x, u)

    sol = solve_ivp(
        rhs,
        (t0, tf),
        np.asarray(x0, dtype=float).reshape(STATE_DIM),
        method="RK45",
        max_step=max_step,
        rtol=rtol,
        atol=atol,
        dense_output=True,
    )

    if not sol.success:
        return ClosedLoopResult(
            t=sol.t,
            x=sol.y.T,
            u=np.zeros((sol.t.size, CONTROL_DIM)),
            success=False,
            message=sol.message,
            attitude="euler",
            observer_id="none",
        )

    n = max(int(np.ceil((tf - t0) / max_step)) + 1, 2)
    t_out = np.linspace(t0, tf, n)
    x_out = sol.sol(t_out).T
    u_out = np.zeros((n, CONTROL_DIM))
    for i, ti in enumerate(t_out):
        meas = MeasurementBus(t=float(ti), x=x_out[i])
        u_out[i] = plant.apply_command(command_source.command(float(ti), meas))

    finite = np.isfinite(x_out).all() and np.isfinite(u_out).all()
    return ClosedLoopResult(
        t=t_out,
        x=x_out,
        u=u_out,
        success=bool(sol.success and finite),
        message=sol.message if sol.success else sol.message,
        attitude="euler",
        x_hat=x_out.copy(),
        observer_id="none",
    )


def _simulate_fixed_step(
    plant: SimPlant,
    command_source: CommandSource,
    *,
    t0: float,
    tf: float,
    max_step: float,
    observer,
    measurement_model: MeasurementModel | None,
) -> ClosedLoopResult:
    """RK4 plant step; controller sees observer estimate (Phase 5d)."""
    dt = float(max_step)
    if dt <= 0:
        msg = "max_step must be > 0 for fixed-step integration"
        raise ValueError(msg)

    n = max(int(np.ceil((tf - t0) / dt)) + 1, 2)
    t_out = np.linspace(t0, tf, n)
    t_out[-1] = tf
    x_out = np.zeros((n, STATE_DIM))
    x_hat_out = np.zeros((n, STATE_DIM))
    u_out = np.zeros((n, CONTROL_DIM))
    project = plant.dynamics.project

    x = plant.x.copy()
    x_out[0] = plant.x_euler()
    x_hat_out[0] = observer.x_hat

    for i in range(n - 1):
        ti = float(t_out[i])
        dti = float(t_out[i + 1] - t_out[i])
        # Control from estimate
        meas_ctrl = MeasurementBus(t=ti, x=observer.x_hat)
        ui = plant.apply_command(command_source.command(ti, meas_ctrl))
        u_out[i] = ui

        def f_at(tt: float, xx: np.ndarray, uu: np.ndarray = ui) -> np.ndarray:
            return plant.derivatives(tt, xx, uu)

        k1 = f_at(ti, x)
        k2 = f_at(ti + 0.5 * dti, project(x + 0.5 * dti * k1))
        k3 = f_at(ti + 0.5 * dti, project(x + 0.5 * dti * k2))
        k4 = f_at(ti + dti, project(x + dti * k3))
        x = project(x + (dti / 6.0) * (k1 + 2 * k2 + 2 * k3 + k4))
        plant.set_state(float(t_out[i + 1]), x)
        x_true = plant.x_euler()
        x_out[i + 1] = x_true

        # Observer: predict then update with (noisy) measurements of true state
        observer.predict(dti, ui)
        if measurement_model is None:
            x_hat_out[i + 1] = observer.update(x_true)
        elif isinstance(observer, IdentityObserver):
            x_hat_out[i + 1] = observer.update(measurement_model.measure(x_true))
        else:
            x_hat_out[i + 1] = observer.update(measurement_model.observe(x_true))

    # Final control sample
    meas_f = MeasurementBus(t=float(t_out[-1]), x=observer.x_hat)
    u_out[-1] = plant.apply_command(command_source.command(float(t_out[-1]), meas_f))

    finite = (
        np.isfinite(x_out).all()
        and np.isfinite(u_out).all()
        and np.isfinite(x_hat_out).all()
    )
    att = plant.dynamics.attitude
    oid = getattr(observer, "id", "unknown")
    return ClosedLoopResult(
        t=t_out,
        x=x_out,
        u=u_out,
        success=bool(finite),
        message=f"{att}/{oid} RK4 ok" if finite else "non-finite state/control",
        attitude=att,
        x_hat=x_hat_out,
        observer_id=str(oid),
    )
