"""Closed-loop integration using plant + command source."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.integrate import solve_ivp

from uavsim.dynamics import CONTROL_DIM, STATE_DIM
from uavsim.interfaces import MeasurementBus
from uavsim.sim.adapters import CommandSource
from uavsim.sim.plant import SimPlant


@dataclass
class ClosedLoopResult:
    t: np.ndarray  # (N,)
    x: np.ndarray  # (N, 12)
    u: np.ndarray  # (N, 4)
    success: bool
    message: str


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
) -> ClosedLoopResult:
    """Integrate nonlinear plant under a command source on [t0, tf]."""
    plant.reset(x0, t0=t0)

    # Store last command for dense output recording via events/sol
    last_u = np.zeros(CONTROL_DIM)

    def rhs(t: float, x: np.ndarray) -> np.ndarray:
        nonlocal last_u
        meas = MeasurementBus(t=t, x=x)
        cmd = command_source.command(t, meas)
        u = plant.apply_command(cmd)
        last_u = u
        return plant.derivatives(t, x, u)

    # Sample controls after the fact by re-evaluating command source on solution
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
        )

    # Uniform-ish output grid for metrics (include endpoints)
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
    )
