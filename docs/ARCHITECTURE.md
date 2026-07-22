# Architecture — `uavsim` / quadrotor-sim

**Status:** v0.7 (stand-up map)  
**Last updated:** 2026-07-22  
**Normative product intent:** [`SPEC.md`](../SPEC.md) (v0.2+)  
**Working agreements:** [`GROK.md`](../GROK.md)  
**How to extend (research users):** [`docs/developer/`](developer/README.md) · backlog [`EXTENSIBILITY_TODO.md`](developer/EXTENSIBILITY_TODO.md)

This document is the **implementation map**: packages, interfaces, data flow, results, systems, and extension points. If code and this doc disagree, fix one of them — do not leave drift.

**Product north star (SPEC §1.3):**  
`vehicle config → dynamics → SIL design/analyze → export controller → HIL → compare SIL↔HIL`  
Core ships the SIL path + export/compare foundations; HIL transports are post-core.

---

## 1. Goals of the architecture

1. Separate **guidance**, **plant**, **control**, **integration**, **metrics**, and **results I/O**.
2. Make **controllers** and **guidance backends** pluggable without rewriting the sim loop.
3. Treat **run artifacts** as a product (schema-versioned, reproducible).
4. Support **systems-heavy core**: local MC, containers, sharded workers.
5. Keep **Python** as the public CLI/orchestration surface with **explicit polyglot boundaries**.
6. Plan for **navigation beyond waypoints → min-snap** without implementing every mode in core.
7. Support the product workflow in SPEC §1.3–1.4:  
   **vehicle → dynamics → SIL control design/analysis → controller export → HIL → fast SIL↔HIL compare.**

User stories (SPEC §1.4) are the acceptance voice for these goals. Architecture supplies the seams; phasing decides when each story ships.

Non-goals here: freezing every numerical library version, or specifying line-level algorithms (see theory notes later).

---

## 2. Technology baseline

| Layer | Choice | Notes |
|-------|--------|-------|
| CLI / glue | Python 3.11+ | Product CLI name: **`uavsim`** |
| Packaging | `uv` + `pyproject.toml` | Import package name: **`uavsim`** (matches CLI; open to revisit once) |
| Config | YAML + Pydantic models | Validate at load; no `eval` of config |
| Default numerics | NumPy / SciPy | ODE, linalg; LQR via SciPy or python-control |
| Tests | `pytest` | Unit + integration; TDD per `GROK.md` |
| Lint/format | `ruff` (+ `mypy` when types settle) | Exact config at skeleton |
| Containers | Docker + Compose | Single study + worker shards |
| License | MIT | |

**Still open (do not block demos):** min-snap QP backend swap, timeseries on-disk format (lean: Parquet), first polyglot hotspot, geometric / SE(3) controller (PID cascade shipped as second law).

---

## 3. Repository layout (target)

```text
quadrotor-sim/
  README.md
  LICENSE
  SPEC.md
  GROK.md
  AGENTS.md
  pyproject.toml              # Phase 0
  configs/
    vehicles/                 # mass, inertia, limits, geometry defaults
    controllers/              # optional shared Q/R / gains snippets
    missions/                 # waypoint files, geometric mission params, …
    studies/                  # composes vehicle + controller + guidance + MC
  src/uavsim/
    __init__.py
    cli/                      # thin entrypoints only
    vehicles/                 # params, actuator limits, factories/loaders
    dynamics/                 # f(x,u,p), linearize, trim helpers for plant
    reference/                # ReferenceTrajectory, evaluate, feasibility, export
    guidance/                 # planners only (no reference type ownership)
      base.py                 # protocol + registry
      waypoints/              # load mission, interp, minsnap, auto-select
      # geometric/ …          # post-core
    control/
      base.py
      lqr.py                  # design uses dynamics.linearize + vehicle params
      pid.py                  # cascade alternate (shipped)
      export.py
    estimation/               # StateObserver, linear_kf, mekf, measurements
    sim/                      # ClosedLoopSim / ODE wiring (+ optional observer)
    metrics/
    studies/                  # load/resolve study → plan → sim → write run
    monte_carlo/
      engine.py
      shard.py
      summary.py
    results/                  # run dir I/O, manifest
    viz/                      # consumers of run dirs only
  containers/
  tests/
    unit/
    integration/
  docs/
    ARCHITECTURE.md
  runs/                       # gitignored local outputs
```

### 3.1 Module responsibilities (pinned)

| Package | Owns | Does **not** own |
|---------|------|------------------|
| `uavsim.vehicles` | Physical params, actuator limits, load/factory from config | Equations of motion |
| `uavsim.dynamics` | `f(x, u, p) → xdot`, linearization, hover/trim helpers for the plant | Controller gains, mission files |
| `uavsim.reference` | Reference trajectory types, `evaluate(t)`, feasibility checks, reference serialization | Planners / waypoint algorithms |
| `uavsim.guidance` | Guidance backends (`plan` / `update`), mission→reference algorithms | Sim loop, metrics, controller internals |
| `uavsim.control` | Controller protocol, LQR + PID, gain design, export | Plant ODEs, guidance backends |
| `uavsim.estimation` | Observers (`none` / KF / MEKF), measurement models, channels | Plant ODEs, guidance, transport drivers |
| `uavsim.sim` | Closed-loop integration, plant step, SIL adapter, observer wire-up | Config loading, run-dir layout policy, device drivers |
| `uavsim.interfaces` (or `plant_io`) | `ActuatorCommand`, `MeasurementBus`, shared I/O schemas | Transport/drivers |
| `uavsim.hil` | Post-core: link adapters, pacing, HIL fixtures | Control law math, guidance |
| `uavsim.studies` | Study resolve + nominal pipeline orchestration | Low-level numerics |
| `uavsim.monte_carlo` | Trial loops, sharding, merge | Duplicate dynamics |
| `uavsim.results` | Manifests, artifact paths, schema-versioned I/O | Plotting |
| `uavsim.viz` | Plots/reports from artifacts | Live sim state |
| `uavsim.cli` | Argument parsing → library calls | Business logic |

**Config rule:** studies **compose**; missions **describe what to fly**.  
Waypoint/mission files live under `configs/missions/`. Studies under `configs/studies/` point at vehicles, controllers, and missions. Do not maintain a parallel `configs/guidance/` or `configs/trajectories/` tree.

### 3.2 Import dependency direction

Allowed edges only (lower must not import upper):

```text
cli → studies → monte_carlo
              → sim → control → reference
              │         ↘ dynamics ← vehicles
              │         ↘ estimation → dynamics, vehicles, interfaces
              │         ↘ vehicles
              │         ↘ interfaces   (commands / measurements)
              → guidance → reference
              │          → vehicles   (limits for planning)
              → metrics
              → results
hil (post-core) → interfaces, sim.plant   # not → guidance.waypoints
viz → results
```

**Hard rules**

- `control` must not import `guidance` or `guidance.waypoints`.
- `control` must not import `hil` or transport drivers.
- `sim` may depend on the **guidance protocol** only for optional `update`, never on a concrete backend.
- `hil` adapters depend on **interfaces + plant step**, not on a specific LQR module.
- `metrics` depends on timeseries + config thresholds, not on planners.
- `viz` reads run directories via `results` (or raw files); no imports from `sim` internals.
- Application code lives under `src/uavsim/`.
- `configs/` is data, not Python.
- No imports from heritage MATLAB paths.

---

## 4. End-to-end data flow

```text
                    ┌─────────────────┐
                    │  Study config   │
                    │  (uavsim.studies)│
                    └────────┬────────┘
     vehicle, controller, guidance, mission, MC, seeds
                             │
         ┌───────────────────┼───────────────────┐
         v                   v                   v
   VehicleParams      GuidanceBackend      Controller
   (vehicles)         (guidance)           (control)
         │                   │                   │
         │            plan(mission, vehicle)     │
         │                   v                   │
         │         ReferenceTrajectory           │
         │         + FeasibilityReport           │
         │         (reference package)           │
         │                   │                   │
         └───────────────────┼───────────────────┘
                             v
                    ClosedLoopSim (sim)
                    dynamics.f / optional observer / optional guidance.update
                             │
              timeseries (+ x_hat) + per-run metrics
                             │
              ┌──────────────┼──────────────┐
              v              v              v
           results         MC engine      viz/report
                         (local|shards)
```

**Core path:** `studies` runs pre-sim `guidance.plan` only.  
**Reserved:** in-loop `guidance.update` for post-core online nav (sim must not assume guidance is static forever).

---

## 5. Core domain contracts

Frames and vectors are defined in SPEC §5. Summarized:

- Control / metrics bus `x ∈ R¹²`: position NED, ZYX Euler, velocity NED, body rates  
- Optional plant `x ∈ R¹³` (`sim.attitude: quat`): position, unit quaternion, velocity, body rates  
- Control `u ∈ R⁴`: thrust `F`, body torques  
- NED / FRD / thrust along −body-z  

Implementation types should name fields explicitly (or document index maps once in `uavsim.reference` / `uavsim.dynamics`).

---

## 6. Guidance architecture

### 6.1 Concepts

| Concept | Responsibility |
|---------|----------------|
| **Mission config** | Declarative request (`type` + type-specific fields) |
| **Guidance backend** | Algorithm: mission (+ vehicle limits) → reference (and optional updates) |
| **Reference trajectory** | Backend-agnostic time-parameterized signal for control/metrics |
| **Feasibility report** | Warnings/failures attached to a reference |

Sim, control, metrics, and MC **must not** depend on waypoint structs or min-snap solver types.

### 6.2 Reference trajectory contract (`uavsim.reference`)

Types and feasibility live in **`uavsim.reference`**, not under `guidance`. Guidance backends *produce* references; they do not redefine the contract.

Minimum capabilities (names illustrative):

```text
ReferenceTrajectory
  t0, tf: float
  backend_id: str
  metadata: mapping          # yaw policy, method, solver, etc.
  evaluate(t) -> ReferenceSample
  # or dense grid export for artifacts

ReferenceSample
  t: float
  position_ned: (3,)
  velocity_ned: (3,) optional but preferred
  acceleration_ned: (3,) optional
  yaw: float optional
  # attitude / rates if a backend provides them for analysis
```

**Requirements**

- Evaluable at arbitrary `t` in `[t0, tf]` (clamp or error policy documented).
- Units/frames fixed: meters, rad, NED, yaw about Down.
- Serializable to run artifacts without Python pickles as the only format.

### 6.3 Guidance backend protocol

```text
GuidanceBackend
  id: str
  plan(mission: MissionConfig, vehicle: VehicleParams, rng?) -> PlanResult
  update(state, t, mission, vehicle, ref, rng?) -> PlanResult | None
     # default: no-op / None (core backends are offline-only)

PlanResult
  reference: ReferenceTrajectory
  feasibility: FeasibilityReport
  diagnostics: mapping
```

**Registry:** backends registered by `id` string; study config selects `guidance.type` / `guidance.backend`.

### 6.4 Mission config polymorphism

Study YAML shape (illustrative):

```yaml
guidance:
  type: waypoints          # discriminator
  mission_file: configs/missions/simple_square.yaml
  method: auto             # auto | interp | minsnap
  yaw_mode: constant       # constant | path_tangent | from_waypoints
  # type-specific fields only under this block
```

Future:

```yaml
guidance:
  type: geometric
  mission_file: configs/missions/helix.yaml
  # or inline path params
```

Unknown `type` → hard error at config load (fail fast).

### 6.5 Core backends (implement in core)

| Backend / method | Role |
|------------------|------|
| `waypoints` + `interp` | MAKIMA-class (or SciPy equivalent) smooth interpolation |
| `waypoints` + `minsnap` | Mellinger-style minimum snap |
| `waypoints` + `auto` | Documented policy on segment timing / aggressiveness |

### 6.6 Feasibility

- Implemented in **`uavsim.reference`** (or a submodule thereof); operates on `ReferenceTrajectory`.
- Warn vs fail thresholds from config (SPEC §12).
- Stored under `runs/.../guidance/` (provenance) and/or alongside reference artifacts.

### 6.7 How to add a guidance backend

1. Define mission schema (Pydantic) with new `type` discriminator.  
2. Implement `GuidanceBackend` (`plan`; `update` if online) under `uavsim.guidance`.  
3. Register in the guidance registry.  
4. Emit a standard `uavsim.reference.ReferenceTrajectory`.  
5. Add unit tests for the backend + one integration test that drives `ClosedLoopSim` without control changes.  
6. Add example under `configs/missions/` + study under `configs/studies/`.  
7. **Also wire** `studies/pipeline._build_guidance` and `guidance_mission_dict` until registry-driven config lands (see developer guide **TODO G-5**).

Step-by-step narrative: [`docs/developer/guidance.md`](developer/guidance.md).

### 6.8 Post-core navigation (planned, not core-complete)

See SPEC §4.2: geometric paths, corridors, MPC/receding horizon, map-aware, mid-sim replan, external ingest, mixed missions. Architecture hooks: polymorphic mission config + optional `update` + reference contract.

---

## 7. Control architecture

### 7.1 Protocol

```text
Controller
  id: str
  compute(t, x, reference_ctx) -> u
  # reference_ctx wraps ReferenceTrajectory evaluation + any controller-specific trim

# LQR specialization
LqrController
  K, u_hover, x_eq from design(vehicle, Q, R)
  # design calls dynamics.linearize / trim; does not own plant ODEs
```

Core loop (conceptual):

```text
ref = reference.evaluate(t)          # uavsim.reference
u = controller.compute(t, x, ref)
u = saturate(u, vehicle.limits)      # limits from uavsim.vehicles
xdot = dynamics.f(x, u, vehicle)     # uavsim.dynamics
```

### 7.2 Implementations

| ID | Status | Notes |
|----|--------|-------|
| `lqr_hover` | Must | Heritage LQR about hover |
| `pid_cascade` or `geometric` | Should | One alternate; pick at implementation |
| others | Roadmap | Gain scheduling, etc. |

### 7.3 How to add a controller

1. Implement protocol; no direct imports of a specific guidance backend.  
2. Extend factory + study config `controller.type` (registry is **TODO C-5**).  
3. Unit test interface + integration smoke on a gentle mission.  
4. Optional comparison study config (same mission, two controllers).  
5. Optional export artifact path for HIL handoff.

Step-by-step narrative: [`docs/developer/control.md`](developer/control.md).

### 7.4 Control-law refinement path (SIL)

Primary workflow for designing and testing laws stays **in-process software-in-the-loop** (SPEC US-C*):

1. Author `vehicles` config; inject `dynamics`.  
2. Implement / tune a `Controller` (pure compute).  
3. Run studies against `reference` (fast iteration, metrics, MC, CI).  
4. **Export** controller artifact (US-D1) when ready for target or HIL.  
5. Optionally bind the same *command/measurement contracts* to external targets (HIL, US-E*).  
6. **Compare** run dirs in `viz` (SIL vs HIL or baseline vs candidate).

Do **not** route every SIL step through a network or device HAL — that slows control design and pollutes unit tests.

### 7.5 Controller export (write-out)

Before HIL is real, define a **versioned export** produced from a design/SIL run:

```text
ControllerArtifact (illustrative)
  schema_version
  controller_id / type
  sample_rate_hz (if discrete)
  u_hover / trim
  gains (e.g. K for LQR) or structured params
  state/measurement convention ids
  vehicle_id / config hash used for design
  code_identity, created_at
```

- SIL can re-load the artifact to prove round-trip.  
- HIL transport maps artifact → on-target tables or streams setpoints/gains as the protocol requires.  
- Export is **not** a substitute for the in-process `Controller` during rapid SIL iteration.

---

## 7A. Execution modes, I/O contracts, and HIL readiness

HIL is **post-core to implement**, **in-scope to design**. The goal is: refine laws in sim now; later attach real flight computers / boards without rewriting plant, guidance, or metrics.

### 7A.1 Do not use one mega-HAL for “all controllers”

Two different problems get conflated:

| Problem | Right seam | Examples |
|---------|------------|----------|
| **Different control laws** | `Controller` protocol (algorithm) | LQR, PID cascade, geometric |
| **Different execution targets / hardware** | **Plant I/O + transport adapters** | In-process Python, UDP peer, serial MCU, future PX4/MAVLink bridge |

A single “hardware abstraction that wraps every controller” usually becomes a god-object. Prefer **layered contracts**:

```text
  Guidance → Reference
       ↓
  Control law  (Controller.compute)     ← algorithm, unit-testable
       ↓
  Actuator command (u or mixer channels)← plant input contract
       ↑
  Measurements / state estimate         ← plant output contract
       ↑
  Plant step (dynamics + optional sensors)
```

For HIL, **something outside the pure control law** owns timing, bytes, and drivers.

### 7A.2 Execution modes (product vocabulary)

| Mode | Plant | Control law | Typical use |
|------|--------|-------------|-------------|
| **SIL** (core) | `uavsim.dynamics` in-process | In-process `Controller` | Design, MC, CI |
| **PIL** (later) | Sim plant | Law on target MCU/processor (or compiled twin) | Timing, fixed-point, CPU budget |
| **HIL** (later) | Sim plant (+ optional real sensors/actuators later) | Real FC / board closes loop over a link | Integration with flight hardware |
| **Open-loop / log replay** | Optional | Optional | Validation, regression |

Core implements **SIL** only. Architecture must not hard-wire “controller is always a Python object in the ODE RHS” without an indirection for *who provides `u` each step*.

### 7A.3 Plant step interface (the important seam)

Factor the sim loop so the plant does not call a concrete Python controller class forever:

```text
PlantSession / SimPlant
  reset(x0, vehicle)
  apply_command(command: ActuatorCommand, t, dt)   # or set_hold
  step(dt) -> PlantOutput
  # or combined step(command, dt) -> PlantOutput

PlantOutput
  t, x_true                     # full state for metrics / logging
  measurements: MeasurementBus  # what a controller is *allowed* to see
  status flags

ActuatorCommand
  # core: body wrench u = [F, τφ, τθ, τψ]
  # future: motor RPMs, PWM, allocation channels — via versioned schema
```

**SIL adapter:** `InProcessControllerAdapter` calls `controller.compute` each step and fills `ActuatorCommand`.

**HIL adapter:** `HilTransportAdapter` sends `MeasurementBus` (and time/ref) to hardware, waits/receives `ActuatorCommand` with timeout policy, feeds plant.

Same plant, metrics, and run artifacts; different **command sources**.

### 7A.4 What belongs in a “HAL” (and what does not)

| Layer | Package (target) | Responsibility |
|-------|------------------|----------------|
| Control law | `uavsim.control` | Math: `compute` → `u` |
| Plant / sensors | `uavsim.dynamics` (+ future `uavsim.sensors`) | Truth state, optional measurement models |
| I/O contracts | `uavsim.plant_io` or `uavsim.interfaces` | `ActuatorCommand`, `MeasurementBus`, schemas, units |
| Transport / HAL | `uavsim.hil` (post-core) | Serial/UDP/MAVLink/…, clock sync, timeouts, packing |
| In-process binding | `uavsim.sim` | Wire SIL adapter + plant + ODE |

**HAL (HIL transport) responsibilities:**

- Byte packing / protocol (versioned)
- Link bring-up and health
- Real-time or soft-real-time pacing (`wall_dt` vs `sim_dt`)
- Watchdog: late/missing packets → fail-safe command or study failure
- **Not** LQR math, not trajectory generation, not metrics definitions

Different boards ⇒ different **transport adapters** behind one plant I/O contract — not different copies of the plant.

### 7A.5 Full-state vs measurements (design rule)

Heritage SIL often assumes full-state feedback (`x` into LQR). That is fine for core LQR.

For HIL-ready design:

- Define **`MeasurementBus`** early even if SIL fills it from full state (`x` → ideal measurements).
- Controllers that need full state take measurements (SIL may fill from `x_true`).  
- **Phase 5d (shipped):** optional `StateObserver` (`linear_kf` / `mekf` / `partial_raw`) between plant outputs and `Controller.compute` — default remains ideal full state (`none`). Channels include GPS-style `pos`/`omega`, AHRS `att`/`omega`, and GPS-denied **`body_vel`/`alt`** (optical-flow + altitude proxy).
- Avoid baking `compute(t, x, …)` as the *only* possible signature forever — prefer:

```text
compute(t, measurements, reference_ctx) -> ActuatorCommand
# SIL convenience: measurements derived from x_true
```

Exact Python protocol can keep a thin full-state wrapper for LQR ergonomics, implemented on top of the measurement-oriented contract.

### 7A.6 Timing and determinism

| Concern | SIL (core) | HIL (later) |
|---------|------------|-------------|
| Clock | Sim time | Sim time paced to wall clock or free-run with logged jitter |
| Step | Variable-step ODE OK | Prefer **fixed-step** plant option for hardware rates |
| Repro | Seeded, deterministic | Log link latency; not bit-identical to SIL |
| Safety | N/A | Timeouts, saturations, estop policy in transport adapter |

Architecture: support a **fixed-step sim mode** (even if default remains `solve_ivp`) so HIL and SIL share the same discrete plant step function.

### 7A.7 Suggested package hooks (no need to implement in Phase 0–1)

```text
src/uavsim/
  interfaces/          # or plant_io/ — ActuatorCommand, MeasurementBus, schemas
  sim/
    plant.py           # step interface over dynamics
    adapters/
      inprocess.py     # Controller → commands (SIL)
      # hil_udp.py     # post-core
  hil/                 # post-core: transports, pacing, fixtures
```

Phase 1 may keep a simple closed-loop function **if** plant step + command application are still separable functions (easy to extract). Reject designs where dynamics, LQR, and UDP are one nested function.

### 7A.8 How to add a HIL target (checklist, post-core)

1. Freeze `MeasurementBus` + `ActuatorCommand` schema version.  
2. Implement transport adapter (link + pack/unpack + timeout).  
3. Run fixed-step plant; log both truth state and bus traffic.  
4. Compare SIL vs HIL metrics on a gentle mission (soft tolerances).  
5. Document wiring, rates, and safety limits; never claim flight certification.

### 7A.9 Non-goals for HIL in this project (unless explicitly promoted)

- Certifying flight software  
- Supporting every autopilot vendor on day one  
- Real motors/props as required core path  
- Replacing SIL as the default design loop  

---

## 8. Vehicles, plant, sim, metrics

### 8.1 Vehicles (`uavsim.vehicles`)

- **Params:** mass, inertia, arm length, gravity, etc.
- **Limits:** thrust/torque saturation bounds (and related envelopes used by sim/control).
- **Factory/loaders:** YAML → validated `VehicleParams` (immutable-ish value objects preferred).
- Does **not** implement `f(x,u,p)` or linearization.

### 8.2 Dynamics (`uavsim.dynamics`)

- Pure functions where practical: `f(x, u, p) -> xdot`.
- `DynamicsModel` protocol with Euler and quaternion rigid-body implementations (D-3).
- SO(3) / geodesic attitude error helpers for control and metrics.
- `linearize(p, equilibrium) -> (A, B)` and hover/trim helpers used by LQR design.
- Saturation applied **before** dynamics in the sim loop (SPEC), using limits from `vehicles`.
- Does **not** load configs or own controller gains.

### 8.2.1 Estimation (`uavsim.estimation`)

- Optional **observer-in-the-loop**: plant truth → noisy / partial measurements → filter → controller bus.
- Types: identity (`none`), hover linear KF, error-state MEKF; partial `channels` selection.
- Logs `x_hat` on timeseries when active. See [developer/estimation.md](developer/estimation.md).

### 8.3 Simulation (`uavsim.sim`)

- `ClosedLoopSim` owns time stepping / ODE interface only.
- Inputs: vehicle params, controller, reference (and optional guidance protocol for `update`).
- Outputs: timeseries structure + flags (success, NaN stop, etc.).
- **No global mutable sim state.**

### 8.4 Metrics

- Pure functions: timeseries + config thresholds → metrics dict / model.
- Same metric code for nominal and each MC trial.
- Success criteria from config (SPEC §11).

### 8.5 Studies pipeline (`uavsim.studies`)

- Resolve study config (paths, seeds, backend selection).
- Nominal path: load vehicle → build controller → `guidance.plan` → feasibility → `ClosedLoopSim` → metrics → `results` write.
- CLI and MC call into this layer rather than re-orchestrating ad hoc.

### 8.6 Multi-airframe extensibility

The architecture is intended to grow **beyond a single quadrotor** without rewriting the SIL core. See [`docs/developer/airframes.md`](developer/airframes.md) and backlog IDs **V-8**, **D-3**, **D-7/D-8**, **D-11/D-12**, **S-7**.

**Seams**

- Pluggable **`DynamicsModel`** (D-3) for custom \(f(x, u, p)\) with optional extra states (tilt angles, airspeed, motor speeds, …). **Shipped:** Euler/quat rigid body + optional first-order motors.
- Generalized **`VehicleParams`** and actuator **mixer** (D-7/D-8 **shipped** for X-quad; body-wrench remains the default controller interface).
- Mode-aware guidance / controllers and trim conditions where the airframe needs them.
- **Airframe selector** in study configs (S-7) so MC and compare can span families.

**Examples (planned, not core-complete)**

- **Tilt-rotor / hybrid VTOL:** variable thrust vectoring, hover / transition / cruise modes, hybrid aero.
- **Others:** fixed-wing, coaxial, etc., as research needs justify.

**Design guardrails** (apply to high-priority work — flex modes, multi-airframe, HIL rig, comms):

1. Keep core **6-DoF rigid-body quadrotor** as the reusable base and default demo path.  
2. Prefer **additive** states / params — do not break the shipped 12-state NED Euler plant.  
3. Preserve **MC perturbations**, **export/compare**, and **viz** compatibility (consumers of run dirs).  
4. Put hardware-specific concerns (myDAQ, NATS, CAN/DDS bridge, ESC RPM) in a **HIL companion** project; this repo owns fixed-step plant + I/O contracts (§7A, D-11).

This enables comparative robustness studies across airframes once S-7 lands, without a core refactor.

---

## 9. Configuration model

Top-level study (illustrative):

```yaml
schema_version: 1
study_id: square_mc_demo
seed: 42

vehicle: configs/vehicles/default_quadrotor.yaml
controller:
  type: lqr_hover
  Q: ...
  R: ...
guidance:
  type: waypoints
  mission_file: configs/missions/simple_square.yaml
  method: auto
  yaw_mode: constant

sim:
  t_end: null            # or override; else from reference horizon
  solver: rk45
  rtol: 1.0e-6

metrics:
  position_bound_m: 0.1

monte_carlo:
  enabled: true
  n_trials: 100
  backend: local         # local | docker
  shards: 1
  perturbations: ...
```

**Validation:** load → Pydantic → resolved absolute paths → frozen copy written into run dir.

---

## 10. Results and manifests

### 10.1 Run directory

```text
runs/<study_id>_<timestamp>/
  manifest.yaml
  study_config.yaml
  guidance/
    backend.json
    feasibility.json
    mission_snapshot.yaml
  reference/                  # backend-agnostic reference artifacts
    reference.*               # e.g. parquet + meta.json
  nominal/
    timeseries.*
    metrics.json
  monte_carlo/                # optional
    trials.*
    summary.json
    shards/                   # optional intermediate
  reports/
    summary.md
  figures/                    # optional post-process
```

### 10.2 Manifest (minimum fields)

- `schema_version`, `study_id`, `created_at`
- `code_identity` (git commit / dirty flag)
- `config_hash`
- `seed`, `n_trials` (if MC)
- `package_versions` (key deps)
- `execution`: `{ mode: local|docker, shards, worker_image? }`
- `status`: success | failed | partial

### 10.3 Timeseries format

**Lean default:** Parquet for dense arrays + JSON for small metrics. Alternatives (HDF5/NPZ) remain open; pick one in Phase 1 and document in `docs/results_schema.md` when frozen.

### 10.4 Multi-run comparison contract (SPEC S10 / US-E3)

`uavsim compare run_a run_b` is a **results consumer** only.

**Inputs:** two run directories with compatible `schema_version` (and ideally same mission/vehicle intent).  
**Outputs (minimum):**

- Metric delta table (RMSE position, max error, success flags, key control stats)
- At least one overlay figure (e.g. position vs time or 3D path) for primary signals
- Short markdown summary under a compare output path or stdout

**Alignment policy (document when implementing):**

- Prefer identical time grids; else resample to a common grid with documented method
- Label runs by `execution.mode` (`sil` | `hil` | …) from manifests when present
- Soft tolerances only — HIL will not match SIL bit-for-bit

**Controller export** (SPEC S9) may live under `artifacts/controllers/` or inside the run dir; compare may optionally annotate which controller artifact each run used.

### 10.5 Quality expectations for artifacts

| Rule | Expectation |
|------|-------------|
| Schema version | Present on metrics, manifests, controller exports |
| No live coupling | `viz` / `compare` / `report` never import sim loop internals |
| Provenance | Manifest records seed, code identity, config hash, execution mode |
| SIL vs HIL parity | Same metric field names and units across modes |

---

## 11. Monte Carlo and systems

### 11.1 Trial purity

Trial `i` RNG stream derived from `(base_seed, i)` (exact algorithm documented in code).  
Default heritage posture: **nominal controller design**, **perturbed plant** parameters (optional redesign-K mode later).

### 11.2 Execution modes

| Mode | Behavior |
|------|----------|
| `local` | Process pool / concurrent futures |
| `docker` | Container image runs study or worker |
| `docker` + `shards > 1` | Partition `0..N-1`; workers write shard artifacts; coordinator merges |

### 11.3 Shard merge

- Disjoint index ranges cover all trials.
- Merge builds full trial table; summary computed on merge.
- Any required shard failure → study **failed** (default).
- Manifest records shard map and worker identity.

### 11.4 Containers

- One primary image: install package + run `uavsim`.
- Compose (or equivalent) for multi-worker demos.
- CI: unit tests always; container/shard smoke when practical (SPEC F12–F14).

---

## 12. Polyglot boundaries

### 12.1 Policy

- Python owns: CLI, config, registry, orchestration, results I/O, default dynamics/control.
- Non-Python allowed behind **narrow interfaces** (e.g. `MinSnapSolver.solve(problem) -> coefficients`).
- Optional components must not break the default install path until they ship as required deps.

### 12.2 Likely hotspots

| Hotspot | Candidate | Interface owner |
|---------|-----------|-----------------|
| Min-snap QP | CasADi / OSQP / cvxpy | `uavsim.guidance.waypoints` |
| Dynamics speed | compiled extension | `uavsim.dynamics` |
| Advanced OCP | CasADi / Julia (later) | new guidance backend |

### 12.3 How to add a polyglot module

1. Define a pure-data problem/result schema in Python.  
2. Implement adapter + optional native code.  
3. Feature-detect or extra dependency group in `pyproject`.  
4. Tests run in CI when the extra is available; skip clearly when not.  
5. Document build in README / containers.

---

## 13. CLI surface

```text
uavsim simulate <study.yaml> [--output runs/...]
uavsim study <study.yaml> [--backend local|docker] [--shards N]
uavsim report <run_dir> [--figures]
uavsim export-controller <run_dir|design.yaml> [--out path]
uavsim compare <run_a> <run_b> [--figures]     # SIL↔SIL or SIL↔HIL
uavsim hil <study.yaml> --transport ...        # post-core
```

Thin wrappers over `uavsim.studies`, `uavsim.monte_carlo`, `uavsim.results`, `uavsim.viz` (not ad-hoc re-wiring of sim internals).

**Viz rule:** `report` / `compare` only read run artifacts (+ optional controller artifacts). Comparison overlays assume shared metric schema and documented time alignment (same mission dt or resample policy).

---

## 14. Testing architecture

| Layer | Location | Focus |
|-------|----------|-------|
| Unit | `tests/unit/` | dynamics invariants, vehicle loaders, LQR poles, schema, metrics, reference feasibility |
| Integration | `tests/integration/` | study pipeline → guidance → sim → metrics; MC N=2 seed; shard merge |
| Contract | either | mock guidance backend drives sim; second controller satisfies protocol |
| Systems | optional/CI | container entrypoint smoke |

No MATLAB bit-parity goldens. Soft metric bands only.

---

## 15. Documentation map (codebase)

| Doc | Owner |
|-----|--------|
| `SPEC.md` | Product requirements / acceptance |
| `ROADMAP.md` | Sequencing / milestones |
| `docs/ARCHITECTURE.md` | This file |
| `GROK.md` | Process |
| `docs/theory.md` (later) | Frames, linearization, LQR, min-snap pointer |
| `docs/results_schema.md` (later) | Frozen artifact schemas |
| `docs/study_authoring.md` (later) | Config how-to |
| `docs/containers.md` | Image + shards |
| `docs/developer/` | Research extend guides (vehicles, control, guidance, dynamics, estimation, airframes) |
| `docs/developer/EXTENSIBILITY_TODO.md` | Plugin / airframe / HIL-rig backlog |
| `docs/viz.md` · `docs/showcase/` | Report figures + portfolio React showcase |
| `README.md` | Human entry / feature overview |

---

## 16. Implementation order (maps to SPEC §19)

| Phase | Focus | Exit signals |
|-------|--------|--------------|
| 0 | Skeleton: `pyproject`, `uavsim`, pytest, ruff, CI stub, thin CLI | importable package, tests run |
| 1 | `vehicles` + `dynamics` + LQR + trivial `reference` + `studies` + SIL adapter + `simulate` | hover/square SIL, run dir |
| 2 | Waypoint `guidance` + feasibility + controller registry + alternate start | ≥3 missions, stub guidance test |
| 3 | Metrics polish + local MC + `study` | seed-stable MC smoke |
| 4 | Docker + shards + assemble | F12–F13 style demos |
| 5 | **Export (S9) + compare (S10)** + multi-run viz; controller compare study | workflow demo without hardware |
| 5b | Visualization pack + showcase | interactive 3D, MC plots, Pages gallery |
| 5c | Quaternion plant + SO(3) error + `DynamicsModel` | aggressive mission path; plant seams |
| 5d | Observer-in-the-loop (KF/MEKF) | control from estimates; default full-state |
| — | Motors / mixer (D-7/D-8) | **Done** (`sim.plant: motors`) |
| — | Aero / GE (D-4/D-5) | **Done** (`AeroParams`, defaults off) |
| — | GPS-denied flow+alt (EST-6) | **Done** (`body_vel`/`alt`; showcase matrix) |
| — | Flex / elastic plant (D-13 / V-7) | **next** SIL plant fidelity |
| 6 | Post-core: non-waypoint guidance | — |
| 7 | Post-core: fixed-step + HIL transport + SIL↔HIL compare | — |

**Expectation:** Phase 5 completes the *software* story of the north-star workflow; Phase 7 attaches hardware without redesigning plant/metrics.

---

## 17. Decision log (architecture)

| Date | Decision |
|------|----------|
| 2026-07-18 | Import package name **`uavsim`** aligned with CLI |
| 2026-07-18 | Guidance protocol + reference contract mandatory before expanding nav modes |
| 2026-07-18 | Timeseries lean default Parquet; freeze later in results schema doc |
| 2026-07-18 | Shard failure fails the study by default |
| 2026-07-18 | **`uavsim.reference`** owns reference types/feasibility; **`guidance`** owns planners only |
| 2026-07-18 | **`vehicles`** = params, limits, factory; **`dynamics`** = `f(x,u,p)`, linearize/trim |
| 2026-07-18 | Config: `configs/missions/` + `configs/studies/` (no parallel trajectories/guidance config trees) |
| 2026-07-18 | **`uavsim.studies`** owns nominal pipeline orchestration; CLI stays thin |
| 2026-07-18 | Import DAG pinned (§3.2); control must not import guidance backends |
| 2026-07-18 | HIL readiness via plant I/O + transport adapters — not a mega-HAL over control laws (§7A) |
| 2026-07-18 | SIL remains default design loop; fixed-step plant option reserved for HIL/PIL |
| 2026-07-18 | Multi-run compare is a results consumer (§10.4); export + compare are Phase 5 (pre-HIL) |
| 2026-07-18 | Align with SPEC v0.2 refined expectations and S9–S11 |
| 2026-07-20 | Multi-airframe extensibility (§8.6): additive dynamics/params; HIL companion for rig; preserve MC/compare/viz |
| 2026-07-20 | Phase **5c** priority: quaternion attitude (D-10) + `DynamicsModel` (D-3) while HIL rig is built in parallel; Euler 12-state remains shipped default until 5c exit |
| 2026-07-20 | Docs audit: `estimation` package + 5c/5d as shipped; layout/DAG/phase table synced |
| 2026-07-22 | Motors/aero/GE shipped; EST-6 flow+alt; phase table next = flex (D-13); showcase controller×sensor matrix |

---

## 18. Changelog

| Version | Date | Notes |
|---------|------|-------|
| v0 | 2026-07-18 | Initial architecture map for stand-up; aligns with SPEC v0.1.1 |
| v0.1 | 2026-07-18 | Layout pin: `reference` vs `guidance`; vehicles/dynamics split; missions config; studies pipeline; import DAG |
| v0.2 | 2026-07-18 | §7A SIL/PIL/HIL modes; plant step + MeasurementBus/ActuatorCommand; hil package hooks |
| v0.3 | 2026-07-18 | Workflow goal; controller export §7.5; compare CLI; ties to SPEC user stories |
| v0.4 | 2026-07-18 | §10.4–10.5 compare/artifact quality; phase table with export/compare before HIL; SPEC v0.2 alignment |
| v0.5 | 2026-07-20 | §8.6 multi-airframe extensibility + developer airframes guide; guardrails for motor/HIL/comms |
| v0.6 | 2026-07-20 | `uavsim.estimation`; DynamicsModel/quat/observer status; doc map + phase rows for 5b–5d |
| v0.7 | 2026-07-22 | Motors/mixer + aero/GE + flow+alt estimation; flex next; phase table sync |

---

*When in doubt: depend on protocols and run artifacts, not on a specific planner or controller implementation.*
