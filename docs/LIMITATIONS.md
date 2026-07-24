# Scope & known limitations

Honest framing for reviewers, employers, and future-you. This is a **research / portfolio SIL** framework, not flight-critical software.

> **Simulation only.** Not certified, not flight-ready, not a substitute for vehicle-specific identification or DO-178-class process.

Deep guides still own the detail: [estimation](developer/estimation.md) · [dynamics](developer/dynamics.md) · [control](developer/control.md) · [EXTENSIBILITY_TODO](developer/EXTENSIBILITY_TODO.md).

---

## What this *is*

- Config-driven **software-in-the-loop** quadrotor GNC: plant → (optional sensors/observer) → control → metrics → run dirs / showcase.
- Teaching-quality **comparisons**: ideal full-state vs partial sensors, LQR vs PID, motors lag, aero/GE, Monte Carlo scatter.
- Explicit **honesty cases** (e.g. gyro-only: position not observable) so bad sensor stacks fail loudly.

## What this is *not*

| Claim someone might assume | Reality |
|----------------------------|---------|
| Production autopilot / PX4 replacement | No. Research SIL with clean seams for later HIL. |
| Classical dual LQG / full nonlinear dual control | **“LQG” here = linear KF + hover LQR** on the same \(K\). PID+KF is cascade on \(\hat x\), not LQG. |
| High-fidelity CFD / BEMT aero | Lumped body drag, prop H-force, optional ground-effect \(\kappa(h)\). **Aero defaults off.** |
| Real IMU / GPS / optical-flow physics | Channel noise + simple models; not bias random walks, multipath, scale-factor maps, etc. |
| Multi-airframe fleet / tilt-rotor | Single X-quad path; multi-airframe is backlog. |
| Flight-test validated numbers | Metrics are **in-sim**; regenerate showcase after model changes. |

---

## Naming & portfolio narrative

### LQR vs LQG vs PID+KF

| Label in docs / showcase | Meaning |
|--------------------------|---------|
| **LQR** | Hover LQR on **true** full state (`observer: none`) |
| **LQG** | Same LQR gains on **linear KF** \(\hat x\) |
| **PID** | Cascade PD on true full state |
| **KF → PID** | Same cascade on \(\hat x\) — **not** classical LQG |

See [estimation.md](developer/estimation.md) and [showcase README](showcase/README.md).

### Ideal full-state is an upper bound

Default SIL (`sim.observer.type: none`) has **no measurement noise** and perfect state. Excellent figure-eight RMSE on that path is expected after correct attitude feedforward + plant consistency — it is **not** a claim about flight hardware.

### Tracking `success`

Peak position error ≤ **3×** study `position_bound_m` and peak attitude error &lt; 45° (SO(3) geodesic). Older looser floors that marked multi-meter AHRS runs as “success” were removed. Details: `uavsim.metrics.tracking`.

---

## Plant & control math (regime)

| Topic | Limitation |
|-------|------------|
| **Linearization** | Hover / small-angle \(A,B\) for LQR design and linear KF. Aggressive flight is outside the design model (envelope tab explores that). |
| **Attitude feedforward** | Hover-thrust inversion at ψ=0: \(\phi=\mathrm{asin}(a_y/g)\), \(\theta=-\mathrm{asin}(a_x/(g\cos\phi))\). Not full differential flatness / geometric tracking (yaw coupling, variable thrust). |
| **PID cascade** | Underactuated small-angle outer loop + attitude PD — comparison baseline, not a geometric controller. |
| **Motors plant** | First-order \(\omega\) lag + X-quad mixer \(f=c_T\omega^2\). No battery, ESC, or inflow dynamics. |
| **Mixer** | Allocation matches FRD \(r \times [0,0,-f]\) for the documented motor map; reaction yaw via \(c_Q/c_T\). Self-consistent SIL; not a drop-in for every airframe mixer. |
| **Aero / GE** | Opt-in, teaching-scale coeffs. LQR linearization includes **linear** drag/rate damping only; quadratic drag, prop H, and ground-effect \(\kappa\) are **not** in \(A,B\). Hover with GE is not trimmed at \(mg\). |
| **Flexible body / multi-rotor families** | Not implemented (see backlog). |

---

## Estimation & sensors

| Topic | Limitation |
|-------|------------|
| **`linear_kf`** | Discrete Euler of hover \(A,B\); process noise is a simple diagonal. |
| **`body_vel` (flow proxy)** | **Truth** measurement is body velocity \(R_{b\to i}^\top v_i\). KF measurement matrix \(H\) uses **hover-linear NED velocity** (\(v_b \approx v_i\) at small tilt). Documented teaching mismatch; state-dependent flow \(H\) is backlog (**EST-7**). |
| **`alt`** | NED \(z\) only — baro/rangefinder stand-in, not terrain-relative AGL sensing. |
| **AHRS columns** | Assume an external attitude source (`att` channel); not a full AHRS algorithm. |
| **IMU-only** | Rates alone **do not** observe position — expect drift / failure. Honesty demo, not a bug. |
| **`partial_raw`** | Unmeasured states set to **0** — deliberate bad baseline. |
| **`mekf`** | Error-state / multiplicative attitude path for demos. The discrete error-state \(F\) is **simplified**: position–velocity coupling and attitude kinematics are present, but the **thrust-tilt block** \(\delta\dot v \leftarrow -R[0,0,-F/m]\times\delta\theta\) is omitted (hover-teaching filter, not full multiplicative EKF). Accel-aided / true IMU physics is backlog (**EST-8**). |
| **Min-snap guidance** | Mellinger-style per-axis QP in code; not independently re-derived against an external reference solver in CI. |

---

## Metrics, MC, and artifacts

| Topic | Limitation |
|-------|------------|
| **RMSE / success** | Relative to the **reference trajectory** and the **plant as modeled**. Cross-run comparisons need the same mission, vehicle, and code revision. |
| **Estimate attitude RMSE** | SO(3) geodesic angle between \(\hat x\) and truth (not raw Euler subtraction). |
| **Monte Carlo** | Parameter scatter (mass / inertia / arm, etc.) as configured — not a full uncertainty budget. |
| **MC observer model** | With default `redesign_controller: false`, the **controller and the observer** are built on the **nominal** vehicle; only the **plant** is perturbed. That matches “fixed law + fixed filter model, uncertain plant.” If the observer were redesigned on the trial vehicle, LQG MC would understate model mismatch. |
| **Showcase JSON** | Built by `uavsim gallery` from study configs. **Can lag code** after plant/control fixes; rebuild before external demos. |
| **Docker MC** | Image must match the tree under test (stale images produce misleading “extra” failures). |

---

## Intentional non-goals (near term)

From product docs / backlog — not missing by accident:

- HIL transport / flight software integration (seams only)
- Wind fields, full BEMT, flexible structures
- Multi-airframe (tilt, hex, VTOL hybrids)
- Certified processes, DO-178, SITL of a specific OEM stack

Track open work in [`EXTENSIBILITY_TODO.md`](developer/EXTENSIBILITY_TODO.md) and [`ROADMAP.md`](../ROADMAP.md).

---

## How to read results in an interview

1. **Ideal LQR/PID** → “Does the closed-loop plant + law work with perfect state?”
2. **Sensor matrix** → “How does the *same* law degrade when the bus is incomplete or filtered?”
3. **Motors / aero / GE** → “What changes when actuators and simple aero are not ideal?”
4. **MC / envelope** → “How sensitive are we to mass/inertia and linearization stretch?”

If a number looks too good or too bad, check: observer type, channels, plant mode, vehicle aero, and whether the showcase was rebuilt after the commit under discussion.

---

## Related

| Doc | Role |
|-----|------|
| [README](../README.md) | Product entry |
| [estimation.md](developer/estimation.md) | Observers, channels, success metric |
| [dynamics.md](developer/dynamics.md) | Plant, motors, aero |
| [control.md](developer/control.md) | LQR / PID |
| [showcase/README.md](showcase/README.md) | Matrix naming and rebuild |
| [SPEC.md](../SPEC.md) | Requirements / MoSCoW |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Package boundaries |
