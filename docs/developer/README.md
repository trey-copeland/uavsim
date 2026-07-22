# Developer & research user guide

Guides for **using** and **extending** `uavsim` without reading the whole tree.

| Guide | Topics |
|-------|--------|
| [Vehicles](vehicles.md) | Define mass properties, limits, point studies at a vehicle YAML |
| [Airframe families](airframes.md) | Quad today; tilt-rotor / multi-airframe vision; HIL rig tie-in |
| [Control](control.md) | Built-in LQR & PID, tuning, adding a new control law |
| [Guidance & navigation](guidance.md) | Hold / waypoints, missions, adding a guidance backend |
| [Dynamics](dynamics.md) | Euler/quat/motors plants, aero/GE, `DynamicsModel`, SO(3); flex next |
| [Estimation](estimation.md) | KF/MEKF/partial_raw, channels (GPS, AHRS, **flow+alt**), `sim.observer` |
| [Extensibility backlog](EXTENSIBILITY_TODO.md) | Consolidated **TODOs** (plugins, flex, airframes, HIL) |

**Related product docs**

| Doc | Role |
|-----|------|
| [`docs/LIMITATIONS.md`](../LIMITATIONS.md) | **Scope & known limitations** (interview / portfolio honesty) |
| [`SPEC.md`](../../SPEC.md) | Requirements and MoSCoW |
| [`docs/ARCHITECTURE.md`](../ARCHITECTURE.md) | Package map, import rules, data flow |
| [`docs/viz.md`](../viz.md) | Reports and figures |
| [`GROK.md`](../../GROK.md) | Process (tests, heritage rules) |

## Mental model

```text
Study YAML
  ├─ vehicle        → VehicleParams (configs/vehicles/)
  ├─ controller     → Controller protocol (lqr_hover | pid_cascade | …)
  ├─ guidance       → GuidanceBackend.plan → ReferenceTrajectory
  └─ sim            → plant (wrench|motors × euler|quat) → optional observer → control → metrics
```

**Hard rules (do not violate when extending)**

1. **`control` must not import `guidance`** (or concrete waypoint types).
2. **`dynamics` owns `f(x,u,p)`** — not gains, not missions. Aero/GE live on `vehicle.aero` + `dynamics/aero.py`.
3. **`reference` is backend-agnostic** — planners produce it; sim/control only `evaluate(t)`.
4. **Viz/report only read run dirs** — never live sim state. Showcase Compare is a pure consumer UI.
5. Prefer **config + registry/factory** over hard-coding new types in the CLI.
6. Controllers always consume **Euler 12-state** \(\hat x\) (or truth); new sensors map through `estimation` channels.

## Frames & state (all guides)

| Item | Convention |
|------|------------|
| Inertial | **NED** (North, East, Down); \(z>0\) toward Earth |
| Body | FRD-like; **thrust along −body-\(z\)** |
| State \(x \in \mathbb{R}^{12}\) (control / metrics bus) | \([p_N, p_E, p_D, \phi, \theta, \psi, v_N, v_E, v_D, p, q, r]\) |
| Plant \(x \in \mathbb{R}^{13}\) (optional) | `sim.attitude: quat` — pos, \(q_{wxyz}\), vel, \(\omega\); see [dynamics.md](dynamics.md) |
| Control \(u \in \mathbb{R}^{4}\) | \([F, \tau_\phi, \tau_\theta, \tau_\psi]\) (N, N·m) |
| Angles | radians in code/config unless a figure says deg |

## Quick research loop

```bash
uv sync --extra dev
# 1) edit configs/vehicles/… and/or configs/studies/…
uv run uavsim simulate configs/studies/hover_nominal.yaml
uv run uavsim report runs/<id>/ --interactive
# 2) add tests under tests/unit or tests/integration
uv run pytest -q
```

## Where code lives

```text
src/uavsim/
  vehicles/     # params only
  dynamics/     # f, linearize, mixer, motors, aero, DynamicsModel, SO(3)
  estimation/   # observers (KF/MEKF/partial_raw), channels, measurements
  reference/    # ReferenceTrajectory, feasibility
  guidance/     # planners + registry
  control/      # laws + factory + export
  sim/          # plant + closed loop (+ optional observer)
  studies/      # study YAML + pipeline
  monte_carlo/  # perturbations + MC engine
  results/      # run dirs
  viz/          # report / gallery consumers
configs/
  vehicles/
  missions/
  studies/
```
