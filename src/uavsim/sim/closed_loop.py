"""Closed-loop integration using plant + command source (+ optional observer)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
from scipy.integrate import solve_ivp

from uavsim.dynamics import CONTROL_DIM, STATE_DIM
from uavsim.estimation.identity import IdentityObserver
from uavsim.estimation.measurements import MeasurementModel
from uavsim.interfaces import MeasurementBus
from uavsim.sim.adapters import CommandSource, InProcessControllerAdapter
from uavsim.sim.plant import SimPlant


@dataclass
class GuidanceLoop:
    """Optional online guidance replan handle (G-6)."""

    backend: Any
    mission: dict[str, Any]
    vehicle: Any
    replan_period_s: float = 0.2
    state_source: str = "truth"  # truth | estimate
    last_replan_t: float = field(default=-1.0e9)
    replan_log: list[dict[str, Any]] = field(default_factory=list)


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
    # Optional battery logs (None when vehicle.battery.enabled is false)
    power_w: np.ndarray | None = None
    soc: np.ndarray | None = None
    energy_wh_remaining: np.ndarray | None = None
    replan_log: list[dict[str, Any]] | None = None


def _attach_battery(result: ClosedLoopResult, plant: SimPlant) -> ClosedLoopResult:
    """Post-process energy series when vehicle.battery.enabled (non-breaking)."""
    from uavsim.vehicles.battery import integrate_battery

    vehicle = getattr(plant, "vehicle", None)
    if vehicle is None:
        return result
    series = integrate_battery(result.t, result.u, vehicle)
    if series is None:
        return result
    result.power_w = series.power_w
    result.soc = series.soc
    result.energy_wh_remaining = series.energy_wh_remaining
    return result


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
    guidance_loop: GuidanceLoop | None = None,
) -> ClosedLoopResult:
    """Integrate nonlinear plant under a command source on [t0, tf].

    - Euler plant + identity observer: SciPy RK45 (legacy path).
    - Quaternion plant and/or non-identity observer: fixed-step RK4 with
      optional measurement noise and Kalman (or other) updates.
    - Online guidance (``guidance_loop``) always uses fixed-step and may rebind
      the adapter reference via ``InProcessControllerAdapter.set_reference``.
    Output ``x`` is always **true** Euler 12-state for metrics.
    Optional battery logs when ``plant.vehicle.battery.enabled``.
    """
    plant.reset(x0, t0=t0)
    obs = observer if observer is not None else IdentityObserver()
    obs.reset(plant.x_euler(), t0=t0)

    # RK45 path is Euler-12 wrench only; motors / quat / observers / G-6 use fixed-step
    use_fixed = (
        plant.dynamics.attitude == "quat"
        or plant.state_dim != STATE_DIM
        or getattr(plant, "plant_kind", "wrench") == "motors"
        or not isinstance(obs, IdentityObserver)
        or guidance_loop is not None
    )
    if use_fixed:
        result = _simulate_fixed_step(
            plant,
            command_source,
            t0=t0,
            tf=tf,
            max_step=max_step,
            observer=obs,
            measurement_model=measurement_model,
            guidance_loop=guidance_loop,
        )
    else:
        result = _simulate_euler_ivp(
            plant,
            command_source,
            t0=t0,
            tf=tf,
            x0=x0,
            max_step=max_step,
            rtol=rtol,
            atol=atol,
        )
    return _attach_battery(result, plant)


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


def _maybe_replan(
    guidance_loop: GuidanceLoop | None,
    command_source: CommandSource,
    *,
    t: float,
    x_true: np.ndarray,
    x_hat: np.ndarray,
) -> None:
    if guidance_loop is None:
        return
    period = float(guidance_loop.replan_period_s)
    if t - guidance_loop.last_replan_t < period - 1e-15 and guidance_loop.last_replan_t > -1e8:
        return
    if guidance_loop.state_source == "estimate":
        state = np.asarray(x_hat, dtype=float)
    else:
        state = np.asarray(x_true, dtype=float)
    adapter = command_source if isinstance(command_source, InProcessControllerAdapter) else None
    if adapter is None:
        return
    plan = guidance_loop.backend.update(
        state,
        t,
        guidance_loop.mission,
        guidance_loop.vehicle,
        adapter.reference,
    )
    guidance_loop.last_replan_t = float(t)
    if plan is None:
        return
    adapter.set_reference(plan.reference)
    entry = {"t": float(t), **(plan.diagnostics or {})}
    guidance_loop.replan_log.append(entry)


def _simulate_fixed_step(
    plant: SimPlant,
    command_source: CommandSource,
    *,
    t0: float,
    tf: float,
    max_step: float,
    observer,
    measurement_model: MeasurementModel | None,
    guidance_loop: GuidanceLoop | None = None,
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

    # Initial replan at t0
    _maybe_replan(
        guidance_loop,
        command_source,
        t=float(t0),
        x_true=x_out[0],
        x_hat=x_hat_out[0],
    )

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

        _maybe_replan(
            guidance_loop,
            command_source,
            t=float(t_out[i + 1]),
            x_true=x_out[i + 1],
            x_hat=x_hat_out[i + 1],
        )

    # Final control sample
    meas_f = MeasurementBus(t=float(t_out[-1]), x=observer.x_hat)
    u_out[-1] = plant.apply_command(command_source.command(float(t_out[-1]), meas_f))

    finite = np.isfinite(x_out).all() and np.isfinite(u_out).all() and np.isfinite(x_hat_out).all()
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
        replan_log=list(guidance_loop.replan_log) if guidance_loop is not None else None,
    )
