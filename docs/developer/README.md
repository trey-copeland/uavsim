# Developer & research user guide

Guides for **using** and **extending** `uavsim` without reading the whole tree.

| Guide | Topics |
|-------|--------|
| [Vehicles](vehicles.md) | Define mass properties, limits, point studies at a vehicle YAML |
| [Control](control.md) | Built-in LQR & PID, tuning, adding a new control law |
| [Guidance & navigation](guidance.md) | Hold / waypoints, missions, adding a guidance backend |
| [Dynamics](dynamics.md) | State model today; drag / aero / alternate plant (gaps + plan) |
| [Extensibility backlog](EXTENSIBILITY_TODO.md) | Consolidated **TODOs** where hooks are incomplete |

**Related product docs**

| Doc | Role |
|-----|------|
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
  └─ sim / metrics  → ClosedLoopSim + run artifacts
```

**Hard rules (do not violate when extending)**

1. **`control` must not import `guidance`** (or concrete waypoint types).
2. **`dynamics` owns `f(x,u,p)`** — not gains, not missions.
3. **`reference` is backend-agnostic** — planners produce it; sim/control only `evaluate(t)`.
4. **Viz/report only read run dirs** — never live sim state.
5. Prefer **config + registry/factory** over hard-coding new types in the CLI.

## Frames & state (all guides)

| Item | Convention |
|------|------------|
| Inertial | **NED** (North, East, Down); \(z>0\) toward Earth |
| Body | FRD-like; **thrust along −body-\(z\)** |
| State \(x \in \mathbb{R}^{12}\) | \([p_N, p_E, p_D, \phi, \theta, \psi, v_N, v_E, v_D, p, q, r]\) |
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
  dynamics/     # f, linearize, rotations
  reference/    # ReferenceTrajectory, feasibility
  guidance/     # planners + registry
  control/      # laws + factory + export
  sim/          # plant + closed loop
  studies/      # study YAML + pipeline
  monte_carlo/  # perturbations + MC engine
  results/      # run dirs
  viz/          # report / gallery consumers
configs/
  vehicles/
  missions/
  studies/
```
