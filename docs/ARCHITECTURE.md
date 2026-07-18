# Architecture — `uavsim` / quadrotor-sim

**Status:** v0 (stand-up map)  
**Last updated:** 2026-07-18  
**Normative product intent:** [`SPEC.md`](../SPEC.md)  
**Working agreements:** [`GROK.md`](../GROK.md)

This document is the **implementation map**: packages, interfaces, data flow, results, systems, and extension points. If code and this doc disagree, fix one of them — do not leave drift.

---

## 1. Goals of the architecture

1. Separate **guidance**, **plant**, **control**, **integration**, **metrics**, and **results I/O**.
2. Make **controllers** and **guidance backends** pluggable without rewriting the sim loop.
3. Treat **run artifacts** as a product (schema-versioned, reproducible).
4. Support **systems-heavy core**: local MC, containers, sharded workers.
5. Keep **Python** as the public CLI/orchestration surface with **explicit polyglot boundaries**.
6. Plan for **navigation beyond waypoints → min-snap** without implementing every mode in core.

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

**Still open (do not block skeleton):** min-snap QP backend, timeseries on-disk format (lean: Parquet), first polyglot hotspot, alternate controller type (PID cascade vs geometric).

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
    vehicles/
    controllers/
    guidance/                 # mission + backend configs (or nested under studies)
    studies/
    trajectories/             # waypoint files (*.yaml / *.wpt-compatible)
  src/uavsim/
    __init__.py
    cli/                      # uavsim entrypoints
    vehicles/
    dynamics/
    guidance/
      base.py                 # protocol + registry
      waypoints/              # load, interp, minsnap, auto-select
      # geometric/ …          # post-core
    trajectory/               # ReferenceTrajectory, evaluation, feasibility
    control/
      base.py
      lqr.py
      # alternate.py          # Should
    sim/
    metrics/
    monte_carlo/
      engine.py
      shard.py
      merge.py
    results/                  # run dir I/O, manifest
    viz/                      # consumers only
  containers/
  tests/
    unit/
    integration/
  docs/
    ARCHITECTURE.md           # this file
    # theory.md, results_schema.md, …
  runs/                       # gitignored local outputs
```

**Rules**

- Application code lives under `src/uavsim/`.
- `configs/` is data, not Python.
- `viz` and `report` never import private sim internals to “reach in” for state; they read run directories.
- No imports from heritage MATLAB paths.

---

## 4. End-to-end data flow

```text
                    ┌─────────────────┐
                    │  Study config   │
                    └────────┬────────┘
           vehicle, controller, guidance, MC, seeds
                             │
         ┌───────────────────┼───────────────────┐
         v                   v                   v
   VehicleParams      GuidanceBackend      Controller
         │                   │                   │
         │            plan(mission, vehicle)     │
         │                   v                   │
         │           ReferenceTrajectory         │
         │           + FeasibilityReport         │
         │                   │                   │
         └───────────────────┼───────────────────┘
                             v
                    ClosedLoopSim
                    (optional guidance.update)
                             │
              timeseries + per-run metrics
                             │
              ┌──────────────┼──────────────┐
              v              v              v
           results/        MC engine     viz/report
                         (local|shards)
```

**Core path:** pre-sim `guidance.plan` only.  
**Reserved:** in-loop `guidance.update` for post-core online nav (sim must not assume guidance is static forever).

---

## 5. Core domain contracts

Frames and vectors are defined in SPEC §5. Summarized:

- State `x ∈ R¹²`: position NED, ZYX Euler, velocity NED, body rates  
- Control `u ∈ R⁴`: thrust `F`, body torques  
- NED / FRD / thrust along −body-z  

Implementation types should name fields explicitly (or document index maps once in `uavsim.trajectory` / `uavsim.dynamics`).

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

### 6.2 Reference trajectory contract

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
  waypoints_file: configs/trajectories/simple_square.yaml
  method: auto             # auto | interp | minsnap
  yaw_mode: constant       # constant | path_tangent | from_waypoints
  # type-specific fields only under this block
```

Future:

```yaml
guidance:
  type: geometric
  path: helix
  # …
```

Unknown `type` → hard error at config load (fail fast).

### 6.5 Core backends (implement in core)

| Backend / method | Role |
|------------------|------|
| `waypoints` + `interp` | MAKIMA-class (or SciPy equivalent) smooth interpolation |
| `waypoints` + `minsnap` | Mellinger-style minimum snap |
| `waypoints` + `auto` | Documented policy on segment timing / aggressiveness |

### 6.6 Feasibility

- Operates on **`ReferenceTrajectory`**, not only waypoint pipelines.
- Warn vs fail thresholds from config (SPEC §12).
- Stored under `runs/.../guidance/`.

### 6.7 How to add a guidance backend

1. Define mission schema (Pydantic) with new `type` discriminator.  
2. Implement `GuidanceBackend` (`plan`; `update` if online).  
3. Register in the guidance registry.  
4. Emit a standard `ReferenceTrajectory`.  
5. Add unit tests for the backend + one integration test that drives `ClosedLoopSim` without control changes.  
6. Document config example under `configs/` and “Study authoring.”

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
```

Core loop (conceptual):

```text
ref = reference.evaluate(t)
u = controller.compute(t, x, ref)
u = saturate(u, vehicle.limits)
xdot = dynamics.f(x, u, vehicle)
```

### 7.2 Implementations

| ID | Status | Notes |
|----|--------|-------|
| `lqr_hover` | Must | Heritage LQR about hover |
| `pid_cascade` or `geometric` | Should | One alternate; pick at implementation |
| others | Roadmap | Gain scheduling, etc. |

### 7.3 How to add a controller

1. Implement protocol; no direct imports of a specific guidance backend.  
2. Register by id; study config `controller.type`.  
3. Unit test interface + integration smoke on a gentle mission.  
4. Optional comparison study config (same mission, two controllers).

---

## 8. Plant, sim, metrics

### 8.1 Dynamics

- Pure functions where practical: `f(x, u, vehicle) -> xdot`.
- Saturation applied **before** dynamics (SPEC).
- Linearization + hover trim live in `vehicles` / `dynamics` as pure design helpers for LQR.

### 8.2 Simulation

- `ClosedLoopSim` owns time stepping / ODE interface only.
- Inputs: vehicle, controller, reference (and optional guidance for `update`).
- Outputs: timeseries structure + flags (success, NaN stop, etc.).
- **No global mutable sim state.**

### 8.3 Metrics

- Pure functions: timeseries + config thresholds → metrics dict / model.
- Same metric code for nominal and each MC trial.
- Success criteria from config (SPEC §11).

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
  waypoints_file: configs/trajectories/simple_square.yaml
  method: auto
  yaw_mode: constant

sim:
  t_end: null            # or override; else from trajectory
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
  trajectory/                 # or trajectory.parquet + meta.json
    reference.*
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
```

Thin wrappers over library functions in `uavsim.sim`, `uavsim.monte_carlo`, `uavsim.results`, `uavsim.viz`.

---

## 14. Testing architecture

| Layer | Location | Focus |
|-------|----------|-------|
| Unit | `tests/unit/` | dynamics invariants, LQR poles, schema, metrics, feasibility |
| Integration | `tests/integration/` | config → guidance → sim → metrics; MC N=2 seed; shard merge |
| Contract | either | mock guidance backend drives sim; second controller satisfies protocol |
| Systems | optional/CI | container entrypoint smoke |

No MATLAB bit-parity goldens. Soft metric bands only.

---

## 15. Documentation map (codebase)

| Doc | Owner |
|-----|--------|
| `SPEC.md` | Product requirements / acceptance |
| `docs/ARCHITECTURE.md` | This file |
| `GROK.md` | Process |
| `docs/theory.md` (later) | Frames, linearization, LQR, min-snap pointer |
| `docs/results_schema.md` (later) | Frozen artifact schemas |
| `docs/study_authoring.md` (later) | Config how-to |
| `docs/containers.md` (later) | Image + shards |

---

## 16. Implementation order (maps to SPEC phases)

0. Skeleton: `pyproject`, package `uavsim`, pytest, ruff, CI stub, empty CLI  
1. Vehicle + dynamics + LQR + trivial reference + `simulate` + run dir  
2. Waypoint guidance (interp/minsnap/auto) + feasibility + controller protocol + registry  
3. Metrics polish + MC local + `study`  
4. Docker + shards + assemble  
5. Polish docs/plots; optional alternate controller if not done  
6. Post-core: first non-waypoint guidance / replan demo when prioritized  

---

## 17. Decision log (architecture)

| Date | Decision |
|------|----------|
| 2026-07-18 | Import package name **`uavsim`** aligned with CLI |
| 2026-07-18 | Layout: `src/uavsim/` with `guidance/` + `trajectory/` split |
| 2026-07-18 | Guidance protocol + reference contract mandatory before expanding nav modes |
| 2026-07-18 | Timeseries lean default Parquet; freeze later in results schema doc |
| 2026-07-18 | Shard failure fails the study by default |

---

## 18. Changelog

| Version | Date | Notes |
|---------|------|-------|
| v0 | 2026-07-18 | Initial architecture map for stand-up; aligns with SPEC v0.1.1 |

---

*When in doubt: depend on protocols and run artifacts, not on a specific planner or controller implementation.*
