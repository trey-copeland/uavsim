# UAVSIM — Quadrotor Simulation & GNC Framework

**Working title / repo:** `quadrotor-sim`  
**CLI / product name:** `uavsim`  
**Status:** Living core specification (v0.2.1)  
**Author:** Trey Copeland  
**Last updated:** 2026-07-18  
**License (intent):** MIT  

**Companion docs**

| Doc | Role |
|-----|------|
| `SPEC.md` (this file) | What / why / scope / acceptance |
| `ROADMAP.md` | Sequencing, milestones, now/next/later |
| `GROK.md` | How we work (GSD, tests, heritage rules) |
| `docs/ARCHITECTURE.md` | Languages layout, packages, FFI, module APIs |
| Language conventions (TBD) | Per-language tooling and idioms |

---

## 0. Decisions closed in this revision

| Topic | Decision |
|-------|----------|
| CLI / product name | **`uavsim`** (`simulate`, `study`, `report`, `export-controller`, `compare`, later `hil`) |
| License | **MIT** |
| Core ambition | **Systems-heavy core** — GNC depth **plus** containerized studies and sharded MC as first-class demos |
| Language posture | **Python-first** with **explicit polyglot boundaries from day one** |
| Package layout | **`src/uavsim/`** per ARCH: `vehicles` / `dynamics` / `reference` / `guidance` / `control` / `sim` / `studies` / … |
| Vehicles vs dynamics | **vehicles** = params, limits, factory; **dynamics** = `f(x,u,p)`, linearize/trim |
| Reference vs guidance | **reference** = trajectory types + evaluate + feasibility; **guidance** = planners only |
| Config taxonomy | **`configs/missions/`** + **`configs/studies/`** (studies compose; missions describe what to fly) |
| Primary workflow | **Vehicle → dynamics → SIL design/analyze → export controller → HIL → SIL↔HIL compare** (§1.3–1.4) |
| SIL vs HIL | **SIL default** design loop; HIL is post-core *implementation* but **first-class product destination** |
| Control vs hardware | **Control law protocol** ≠ **plant I/O / transport HAL** — no mega-HAL over algorithms |
| Second controller | **Should for core** (one non-LQR impl + comparison study) |
| Controller export | **Should for core** — versioned artifact (gains/trim/metadata); required before serious HIL |
| Multi-run compare | **Should for core** — `uavsim compare` on two run dirs (SIL↔SIL now; SIL↔HIL when HIL exists) |
| Academic paper | **Cite only** |
| Guidance / navigation | Pluggable stack; core ships waypoint interp + min-snap; not the only mission model forever |

Still open (see §18): min-snap solver backend, timeseries format freeze, alternate controller type, first polyglot hotspot, first post-core nav mode, remote GitHub timing, HIL transport choice.

---

## 1. Purpose

Build a modern, public-facing **quadrotor UAV simulation and GNC analysis framework** that demonstrates professional competence in:

- Flight dynamics and coordinate conventions (aerospace NED)
- Trajectory generation, **guidance/navigation**, and feasibility
- Feedback control design and closed-loop simulation
- Robustness analysis under parametric uncertainty
- Reproducible experiment / results pipelines
- **Software systems for GNC** — config-driven studies, artifacts, CI, containers, and scalable MC workers
- Architecture suitable for extension beyond a single controller, vehicle, **or navigation mode** (**polyglot-ready boundaries**)

This is **not** a line-for-line port of the prior MATLAB ME590 codebase. That project established domain correctness and research outcomes; it also accumulated structural and architectural debt. This specification captures **core capability and design intent**. Detailed package layout, FFI choices, and numerical libraries are refined in the architecture document and during stand-up.

### 1.1 Success definition (portfolio lens)

A hiring manager or technical interviewer should be able to clone the repo, run a documented study, and clearly see:

1. Sound GNC engineering (models, control, metrics, uncertainty)
2. Clean interfaces between **guidance** / plant / controller / analysis
3. Reproducible results with a deliberate experiment pipeline
4. **Systems thinking** — config-driven studies, containerized execution, sharded MC with a single assembled summary
5. A credible roadmap: richer navigation, controller export, and HIL with **fast SIL comparison** (not a second disconnected toolchain)

### 1.2 Problem / opportunity (GSD)

**Problem:** Strong ME590 domain work is trapped in a private MATLAB tree with architectural debt and a paper-output tangle unsuitable as a public GNC portfolio piece.

**Opportunity:** Rebuild the capability as `uavsim`: clear GNC story, modern ops (tests, CI, containers, orchestration), and an extensible control/results architecture — without requiring numerical parity with MATLAB.

### 1.3 Primary engineering workflow (product north star)

Ideal loop for a GNC engineer using `uavsim` (SIL-heavy now; HIL when the harness exists):

```text
1. Vehicle config     → define plant params & actuator limits
2. Inject dynamics    → nonlinear model (+ linearize for design)
3. Develop control    → implement/tune law against reference mission
4. Analyze            → metrics, plots, MC robustness, feasibility
5. Write controller   → export / deploy artifact the target can run
                        (codegen, config+gains dump, or firmware handoff)
6. HIL test           → same mission + plant I/O; real (or target) controller
7. Compare SIL ↔ HIL  → shared metrics + visualization for fast diff
```

**Implications for the solution (non-negotiable design pressures):**

| Workflow step | Solution must provide |
|---------------|----------------------|
| Vehicle config | Data-driven vehicle model; no hard-coded mass properties in laws |
| Inject dynamics | Pure plant (`f`, linearize) separable from control and I/O |
| Develop & analyze | Fast **SIL** studies, metrics, artifacts, optional MC |
| Write controller | **Export contract**: versioned gains/params (and later code) from a designed law |
| HIL | Same **plant I/O** + mission/reference; transport adapter supplies commands |
| Compare | **Comparable run artifacts** (same metric schema, aligned time base) + **comparison viz** |

SIL remains the default inner loop. HIL and write-out are first-class *product destinations*, not afterthoughts — even when implementation is phased (see user stories and MoSCoW).

### 1.3.1 Refined product expectations (how we judge “good”)

These expectations govern design reviews and acceptance — not only feature checklists.

| Expectation | Meaning |
|-------------|---------|
| **One plant, many command sources** | SIL in-process controller and future HIL transport feed the **same** plant step and metrics. |
| **Comparable by construction** | Every run writes schema-versioned metrics/timeseries so two runs can be diffed without custom scripts. |
| **Fast inner loop** | Control tuning does not require containers, network, or hardware. |
| **Honest write-out** | Export captures units, frames, trim, gains, and design provenance — not pickle-only blobs. |
| **Viz is a consumer** | Plots/compare never reach into live sim state; they only read run dirs (and optional controller artifacts). |
| **Laptop demos always work** | Portfolio path is SIL-only; HIL is additive (US-E5). |
| **No certification theater** | Sim/HIL harness only; README states simulation-only. |
| **Earn complexity** | Registries and interfaces yes; plugin frameworks and multi-repo packaging only when a second backend/controller forces them. |

---

## 1.4 User stories

Stories use the voice of primary personas. **Priority** maps to delivery phases (not all are core-complete).

**Personas**

| ID | Persona | Goal |
|----|---------|------|
| P1 | **GNC engineer** (primary) | Design, analyze, and harden control for a quadrotor model |
| P2 | **Embedded / integration engineer** | Run the law against hardware or a target with clear I/O |
| P3 | **Reviewer / interviewer** | Clone, run demos, understand architecture in one sitting |
| P4 | **Future self / collaborator** | Reproduce a study months later from artifacts alone |

### Epic A — Vehicle & plant

| ID | As a… | I want… | So that… | Priority |
|----|--------|---------|----------|----------|
| US-A1 | GNC engineer | to author a **vehicle config** (mass, inertia, geometry, limits) | the plant and controllers share one source of truth | **Must** (core) |
| US-A2 | GNC engineer | to **inject modeled dynamics** (nonlinear 6DOF + linearization) without rewriting the sim harness | I can change the vehicle model safely | **Must** (core) |
| US-A3 | GNC engineer | actuator limits applied consistently in sim | saturation behavior is visible in analysis | **Must** (core) |

### Epic B — Guidance & mission

| ID | As a… | I want… | So that… | Priority |
|----|--------|---------|----------|----------|
| US-B1 | GNC engineer | to define missions (waypoints first) and get a **reference trajectory** | I can test tracking on realistic paths | **Must** (core) |
| US-B2 | GNC engineer | feasibility warnings before a long study | I don’t waste runs on impossible yaw/attitude demand | **Should** (core) |
| US-B3 | GNC engineer | to plug in **non-waypoint** guidance later | navigation can grow without a rewrite | **Could** (post-core impl; **Must** design) |

### Epic C — Control design & SIL analysis

| ID | As a… | I want… | So that… | Priority |
|----|--------|---------|----------|----------|
| US-C1 | GNC engineer | to implement a control law behind a stable interface and run **closed-loop SIL** | I can iterate in seconds–minutes | **Must** (core) |
| US-C2 | GNC engineer | to tune LQR (or other) weights via config and see tracking/effort metrics | design tradeoffs are explicit | **Must** (core) |
| US-C3 | GNC engineer | **plots and a short report** from a run directory | I can analyze without ad-hoc scripts | **Must** (core) |
| US-C4 | GNC engineer | **Monte Carlo** under param uncertainty with fixed seeds | I can judge robustness, not one lucky run | **Must** (core) |
| US-C5 | GNC engineer | to compare **two control laws** on the same mission/vehicle | I can justify the chosen law | **Should** (core) |
| US-C6 | GNC engineer | CI-protected invariants (trim, stability smoke, schema) | regressions don’t silently break the plant | **Must** (core) |

### Epic D — Write / deploy controller

| ID | As a… | I want… | So that… | Priority |
|----|--------|---------|----------|----------|
| US-D1 | GNC engineer | to **export** a designed controller as a versioned artifact (gains, trim, sample rate, units, schema id) | HIL/firmware isn’t fed by tribal copy-paste | **Should (core)**; **Must** before serious HIL |
| US-D2 | Embedded engineer | a documented mapping from export → on-target representation | bring-up doesn’t reverse-engineer Python objects | **Should** (with HIL path) |
| US-D3 | GNC engineer | optional **codegen or compiled twin** later | PIL can match SIL structure | **Could** (post-core) |

“Write to controller” in v1 means at least **structured export + load path**, not necessarily auto-flashing an FC.

### Epic E — HIL / PIL & SIL comparison

| ID | As a… | I want… | So that… | Priority |
|----|--------|---------|----------|----------|
| US-E1 | Integration engineer | to run the **same study/mission** with commands from an external target (HIL/PIL) | hardware closes the loop against our plant | **Could** impl; **Must** architecture |
| US-E2 | GNC engineer | HIL runs to produce the **same metrics schema** as SIL | comparison is automatic, not spreadsheet archaeology | **Must** (with HIL) |
| US-E3 | GNC engineer | **comparison visualization** (overlay time series, metric deltas) for two runs (SIL↔SIL or SIL↔HIL) | I can spot divergence in minutes | **Should (core)** for multi-run compare; HIL as second run when available |
| US-E4 | Integration engineer | timeout / fail-safe behavior when the link drops | bad HIL sessions fail loudly and safely | **Must** (with HIL) |
| US-E5 | Reviewer | a documented SIL-only path that never requires hardware | portfolio demos always work on a laptop | **Must** (core) |

### Epic F — Systems, reproducibility, portfolio

| ID | As a… | I want… | So that… | Priority |
|----|--------|---------|----------|----------|
| US-F1 | Collaborator | config + manifest + seeds in every run dir | I can reproduce results | **Must** (core) |
| US-F2 | GNC engineer | containerized and/or sharded MC | large studies finish and demo systems skill | **Must** (core, systems-heavy) |
| US-F3 | Reviewer | one README path from clone → first plot | the project is credible in an interview | **Must** (core) |

### Story → architecture mapping (summary)

| Stories | Architectural pressure |
|---------|------------------------|
| A*, C* | `vehicles` / `dynamics` / `control` / `sim` separation; SIL adapter |
| B* | `guidance` + `reference` contracts |
| C3, E3 | `results` + `viz` as **multi-run consumers** (compare mode), not sim-entangled plots |
| D* | Controller **export schema** next to control design outputs |
| E* | Plant I/O (`ActuatorCommand` / `MeasurementBus`) + `hil` transports; fixed-step option |
| F* | Study pipeline, manifests, containers/shards |

Detailed seams: `docs/ARCHITECTURE.md` (§3, §7, §7A).

---

## 2. Heritage and relationship to ME590

### 2.1 Source of truth for domain behavior

Prior work lives under ME590 `code/` (MATLAB). Useful as **domain reference**, not as architectural target.

**Path (local / WSL):**  
`/mnt/d/Users/Trey/My Drive/Grad School UTK/Course Work/ME590/code`  
(Windows: `D:\Users\Trey\My Drive\Grad School UTK\Course Work\ME590\code`)

| Area | Heritage capability | Port posture |
|------|---------------------|--------------|
| 6DOF nonlinear plant | Rigid-body quadrotor, NED, full Euler kinematics | **Keep as shipped core**; Phase **5c** moves toward quaternion/SO(3) kinematics for larger-attitude missions (see ROADMAP) |
| Linear hover model + LQR | A/B linearization, Riccati gains, hover trim | **Keep as first controller** |
| Waypoints → trajectory | JSON `.wpt`, MAKIMA vs minimum-snap, auto select | **Keep as first guidance backend; redesign as pluggable APIs** |
| Feasibility checks | Yaw rate/accel, attitude vs linearization validity | **Keep; make first-class on reference trajectories** |
| Closed-loop ODE sim | Reference tracking, saturation-aware plant | **Keep; clean orchestration** |
| Monte Carlo | Mass / inertia / geometry uncertainty, stats | **Keep; redesign I/O, parallelism, workers** |
| Metrics & reporting | RMSE tracking, control effort, success flags | **Keep metrics concepts; rebuild pipeline** |
| Paper figure scripts | Ad-hoc MATLAB plotting / LaTeX snippets | **Do not reproduce** (cite paper only) |

Supporting research PDFs, course notes, and the authored paper are **out of scope** for the product tree. Narrative may cite them; validation does not require private Drive assets at runtime.

### 2.2 Explicit non-goals for core

- Numerical parity with MATLAB outputs
- Faithful reproduction of ME590 directory layout or script entrypoints
- Pure-Python purity mandate (polyglot is intentional)
- Bit-identical figure recreation from the paper
- Shipping every “future work” idea from the MATLAB README on day one
- Flight-critical / certification claims

---

## 3. Problem statement

### 3.1 Engineering problem

Support the **vehicle → dynamics → control design (SIL) → analyze → write controller → HIL → compare** workflow: produce trackable references, simulate closed-loop tracking, evaluate performance and robustness, export laws for targets, and—when hardware is attached—run comparable HIL sessions with the same metrics and fast visual diff against SIL.

Core missions are primarily **waypoint-defined** today; the product problem includes growing navigation beyond offline min-snap on fixed waypoints without rewriting the sim loop.

### 3.2 Career / product problem

The public project must read as **GNC engineering plus systems engineering**, not “MATLAB homework rehosted.” Architecture, documentation, reproducibility, and demo surface matter as much as the equations.

---

## 4. Scope

### 4.1 In scope (core v1) — systems-heavy

1. **Vehicle model**
   - Rigid-body 6DOF nonlinear dynamics
   - Linearized hover model for LQR synthesis
   - Explicit actuator limits
   - Configurable physical parameters (mass, inertia, arm length, gravity)

2. **Coordinate conventions**
   - Inertial: NED (North-East-Down)
   - Body: forward-right-down
   - Attitude: **ZYX Euler** (yaw–pitch–roll) in core v1; body rates `p,q,r`. **Planned (Phase 5c):** unit-quaternion / SO(3) plant kinematics with an error-state control path so aggressive mission profiles are first-class (not blocked on HIL hardware).
   - Thrust along −body-z; gravity along +inertial-z

3. **Guidance / navigation subsystem** (extensible; see §5.4, §7)
   - **Reference trajectory** as the product of guidance: time-parameterized state (and derivatives as needed) plus metadata — **independent of how it was generated**
   - **Core v1 backends** (waypoint family):
     - Load waypoint missions (versioned JSON-compatible schema; evolve from heritage `.wpt`)
     - Smooth interpolation (heritage: MAKIMA-class)
     - Minimum-snap optimization (heritage: Mellinger & Kumar style)
     - Optional automatic method selection based on segment timing / aggressiveness
   - Pre-sim **feasibility** reporting on the generated reference (warnings + hard limits)
   - **Architecture requirement:** guidance is a **pluggable interface** (like controllers). Waypoint + min-snap is implementation family #1, not the permanent shape of “mission.”
   - Post-core navigation modes are **in-scope for planning** (interfaces, config shape, sim hooks) even when not implemented in core — see §4.2

4. **Control subsystem**
   - Pluggable controller interface
   - Implementation #1: **LQR about hover**  
     `u = u_hover − K (x − x_ref)` with design weights `Q`, `R`
   - Implementation #2 (**Should**): alternate controller (PID cascade **or** simple geometric) on the **same** interface
   - Reference consumption via a stable **reference context** API (evaluate at `t`, not ad-hoc coupling to min-snap internals)
   - Fair comparison path: same mission + vehicle + metrics, swap controller (and, later, swap guidance backend)

5. **Simulation subsystem**
   - Closed-loop integration of nonlinear plant under chosen controller
   - Deterministic seeding for stochastic components (MC)
   - Structured results (time histories + metrics + config snapshot)

6. **Metrics**
   - Position / attitude / velocity tracking errors (RMSE, max, final)
   - Time-in-bounds (configurable tolerance; heritage default ~0.1 m)
   - Control effort and saturation statistics
   - Success / failure criteria (stable completion, bounds, divergence)

7. **Monte Carlo robustness**
   - Configurable parametric uncertainty (e.g. mass, inertia, geometry)
   - Parallel trial execution (local process pool **and** container workers)
   - **Sharded orchestration** — split trials across workers/containers, assemble one summary
   - Aggregate statistics, distributions, correlation / sensitivity views
   - Seeded reproducibility end-to-end (including shard assembly)

8. **Results pipeline (redesigned)**
   - Config-driven study definition → run → artifacts
   - Machine-readable results + human reports
   - Plot generation as a **consumer** of results, not entangled with the simulator
   - Run manifests (git hash, config hash, environment, seeds, worker topology when sharded)

9. **Public engineering surface**
   - Clear README, architecture notes, API docs
   - Example missions (hover, square / gentle path, figure-eight class)
   - Tests that protect physics and interfaces
   - **Container image + documented one-command study**
   - **CI** (tests + lint + small MC smoke)

10. **Polyglot readiness (day one)**
    - Documented module boundaries where non-Python may live (e.g. min-snap QP, dynamics hotspots, advanced optimal control)
    - Python remains the **orchestration and public CLI** surface unless architecture revises that
    - No requirement to ship a second language in the first merge; **interfaces and packaging must not block it**

### 4.2 Explicitly deferred (post-core) — implement later, design for now

Documented as roadmap, not core-complete *implementation* commitments. **Architecture and interfaces must leave a path** (see §7.5).

**Navigation / guidance (priority expansion area)**

- Geometric / analytic paths (circles, helices, landing profiles) without waypoint JSON
- Motion primitives / library-based maneuvers
- Corridor- or constraint-aware planning (polytope / safe flight corridor class methods)
- Receding-horizon / MPC-style reference generation (online or batch-receding)
- Map- or occupancy-aware planning (even simple 2.5D obstacles)
- Reactive or event-triggered replanning mid-sim (guidance called inside the sim loop, not only pre-sim)
- External trajectory ingest (log replay, offboard planner files, hardware streams)
- Multi-segment missions mixing backends (e.g. takeoff primitive → min-snap transit → hover)

**Other GNC / product**

- ~~Sensor models and EKF / state estimation~~ → **Promoted to Phase 5d (ROADMAP)** — ideal full-state bus remains default; observer-in-the-loop is in-scope SIL before HIL  
- Motor dynamics, propeller maps, allocation (+/X configs) beyond torque/thrust interface
- Environment: wind, drag, ground effect, rotor interaction
- Multi-vehicle / formation
- Gain scheduling, adaptive / robust advanced controllers (beyond LQR + one alternate)
- **HIL / PIL execution** (real FC or target processor in the loop) — **design seams in ARCH §7A**; not a core implementation commitment
- Full interactive web UI (static results gallery is optional flex, not required)

Deferred items should **not** force core interfaces into a dead end (see §7).

---

## 5. Domain model (core physics & GNC)

### 5.1 State vector (12)

```
x = [x, y, z, φ, θ, ψ, ẋ, ẏ, ż, p, q, r]ᵀ
```

| Indices | Quantity | Frame | Units |
|---------|----------|-------|-------|
| 1–3 | Position | NED inertial | m |
| 4–6 | Euler angles roll/pitch/yaw | — | rad |
| 7–9 | Linear velocity | NED inertial | m/s |
| 10–12 | Angular rates | Body | rad/s |

### 5.2 Control vector (4)

```
u = [F, τ_φ, τ_θ, τ_ψ]ᵀ
```

| Element | Meaning | Units |
|---------|---------|-------|
| F | Total thrust | N |
| τ_φ, τ_θ, τ_ψ | Body torques | N·m |

Heritage-scale vehicle (500 g class, tunable): mass ~0.5 kg, arm ~0.25 m, diagonal inertias on order 1e-2 kg·m². Exact defaults live in vehicle config, not hard-coded call sites.

### 5.3 Plant equations (conceptual)

Nonlinear rigid body (heritage form to preserve):

- Kinematics: position rate = velocity; Euler rates from body rates
- Translation: `m · v̇ = R_b→i · [0, 0, −F]ᵀ + [0, 0, m g]ᵀ`
- Rotation: `I · ω̇ = τ − ω × (I ω)`
- Actuator saturation applied on `u` before dynamics

Linear model for LQR: hover equilibrium, small-angle approximation, standard underactuated quadrotor A/B structure.

### 5.4 Guidance products: mission → reference trajectory

Separate three concepts in design (names may refine in architecture):

| Concept | Role |
|---------|------|
| **Mission / guidance request** | What the vehicle should accomplish (waypoints, geometric path params, planner settings, online policy id, …) |
| **Guidance backend** | Algorithm that turns a request (+ vehicle limits) into a reference — or updates it over time |
| **Reference trajectory** | Time-parameterized signal the controller and metrics consume |

A **reference trajectory** is sufficient for tracking when it provides at least:

- Horizon and time base (grid and/or evaluable at arbitrary `t`)
- Position (and typically velocity / acceleration / yaw as required by the active controller)
- Yaw policy metadata when relevant (explicit vs path-tangent vs other)
- Provenance: which backend + config produced it
- Feasibility metadata (from checks run on this reference)

**Core v1 guidance family:** offline waypoint missions → interp or min-snap → full-horizon reference → sim.

**Architecture must also allow (without core implementation):**

- Backends that never see a `.wpt` file
- References that are **recomputed or extended during simulation** (replan hook)
- Studies that swap guidance backends the same way they swap controllers

**Known domain lesson (carry forward):** auto-yaw on tight curves (figure-eights) often produces infeasible yaw rates. Constant yaw is often the correct default for demonstration trajectories; feasibility checks must surface this early.

### 5.5 LQR design sketch

```
ẋ = A x + B u          # linearized about hover
K = lqr(A, B, Q, R)
u = u_hover − K (x − x_ref)
```

Default weight philosophy (heritage): prioritize position/altitude; moderate thrust cost; higher torque cost. Aggressive weights remain a first-class configuration knob.

### 5.6 Alternate controller (Should)

Second implementation must:

- Use the same `controller.compute(t, x, reference_ctx) → u` contract (exact signature refined in architecture)
- Run under the same plant, saturation, metrics, and study configs
- Be documented with limitations (e.g. operating regime) so comparison is honest

Candidate: PID cascade **or** simple geometric — pick one at architecture / Phase 1–2 design; do not implement both for core.

---

## 6. Functional requirements

Requirements use MoSCoW for prioritization within **systems-heavy core**.

### 6.1 Must

| ID | Requirement |
|----|-------------|
| F1 | Load a waypoint mission from a versioned schema (first mission type) |
| F2 | Generate a smooth reference trajectory from waypoints (interp and/or min-snap) |
| F2a | Expose a **guidance/reference interface** so non-waypoint backends can be added without rewriting sim/control/metrics |
| F3 | Design an LQR controller from vehicle + weight config |
| F4 | Simulate closed-loop nonlinear dynamics with reference tracking |
| F5 | Compute standard tracking and control metrics |
| F6 | Run Monte Carlo parameter studies with fixed seed |
| F7 | Persist run config + results + metrics as structured artifacts |
| F8 | Produce a minimal human-readable study report (text or markdown) |
| F9 | Provide ≥3 example missions (hover, gentle path, aggressive path) |
| F10 | Automated tests for dynamics invariants, LQR stabilizability, waypoint I/O, and a smoke closed-loop run |
| F11 | Study definition as data (YAML/TOML/JSON) with thin CLI (`uavsim`) |
| F12 | Container image capable of running a documented study without host MATLAB or tribal paths |
| F13 | Sharded MC path: partition trials, run workers, assemble single summary + manifest |
| F14 | CI: unit/integration tests + lint + small MC smoke on PR |
| F15 | Documented extension point for non-Python modules (boundary + packaging intent) |

### 6.2 Should

| ID | Requirement |
|----|-------------|
| S1 | Automatic *waypoint* method selection (interp vs min-snap) with documented policy |
| S2 | Minimum-snap generator with explicit solver backend choice |
| S3 | Feasibility gate with warn vs fail thresholds (operates on reference trajectories, not only waypoint pipelines) |
| S3a | Study config selects guidance backend by name/id (parallel to controller selection) |
| S4 | Parallel local MC workers (process pool) in addition to container path |
| S5 | Plot pack: 3D tracking, time series, control inputs, MC distributions / sensitivity (**detail §11A**) |
| S5a | Viz/report APIs accept **one or more run directories** (multi-run consumers; US-E3) |
| S5b | Interactive 3D flight view (HTML): rotate scene, playback, vectors + absolute HUD (**§11A**) |
| S6 | Second controller behind the same interface + comparison study example |
| S7 | Controller-comparison study config (same mission, LQR vs alternate) |
| S8 | Static results gallery (HTML) generated from a tagged release run |
| S9 | **Controller export artifact** (versioned gains/trim/metadata) + round-trip load in SIL (US-D1) |
| S10 | **`uavsim compare`** — overlay key time series + metric delta table for two run dirs (SIL↔SIL minimum) |
| S11 | Plant step separable from in-process controller (SIL adapter pattern; enables future HIL without rewrite) |

### 6.3 Could (stretch after core narrative is solid)

| ID | Requirement |
|----|-------------|
| C1 | Lightweight queue (Redis/RQ, Celery, etc.) behind the same study API as Compose workers |
| C2 | Interactive results browser beyond static HTML |
| C3 | First shipped polyglot hotspot (e.g. CasADi min-snap or compiled dynamics) with CI coverage |
| C4 | Additional vehicles or allocation models |
| C5 | First *non-waypoint* guidance backend (e.g. geometric path or simple replan demo) as portfolio extender |
| C6 | Fixed-step plant mode + documented plant I/O contracts (`ActuatorCommand` / `MeasurementBus`) exercised in SIL |
| C7 | First HIL or PIL transport adapter (e.g. UDP loopback or serial fixture) with timeout/fail policy |
| C8 | Full SIL↔HIL comparison study using exported controller + transport (builds on S9–S10) |

### 6.4 Won’t (core)

- Full digital twin of a commercial airframe
- Certified flight software claims
- Replicating ME590 paper figure / LaTeX snippet pipeline
- Runtime dependency on the MATLAB tree or private Drive

---

## 7. Architecture principles

Corrections relative to MATLAB heritage; **detailed layout lives in the architecture doc**.

1. **Separation of concerns**  
   Guidance, reference, plant, controller, integrator, metrics, and reporting must not share mutable global state.

2. **Controller as interface, not hard-wired LQR**  
   Core loop: `u = controller.compute(t, x, reference_ctx)`. LQR is implementation #1; alternate is implementation #2.

2b. **Guidance as interface, not hard-wired waypoints → min-snap**  
   Pre-sim (and optionally in-loop): `reference = guidance.plan(mission_ctx, vehicle_ctx)` and/or `guidance.update(...)`.  
   Waypoint interp/min-snap are backends in one family. Sim, control, metrics, and MC must depend on the **reference trajectory contract**, not on waypoint structs or min-snap solver types.

3. **Config over script spaghetti**  
   Studies defined as data. CLI is thin. Guidance backend and controller are both selectable fields.

4. **Results as a product**  
   Simulation writes a schema-versioned run directory. Plotting and galleries are offline consumers.

5. **Reproducibility by construction**  
   Manifest captures seeds, package versions, config hashes, code identity, and (when used) shard/worker topology.

6. **Extensibility without premature framework theater**  
   Small protocols / clear modules. Earn deeper abstractions when the second controller, second guidance family, and first polyglot module land — but **do not** collapse mission == waypoints in public APIs.

7. **Polyglot from day one, boundaries explicit**  
   Python owns CLI, config, study orchestration, and default numerics unless architecture says otherwise. Hotspots may use other languages behind stable interfaces; document why and how to build/test them.

8. **Systems path is product, not afterthought**  
   Containers and sharded MC are in **core acceptance**, not blogware.

9. **Public repo hygiene**  
   MIT license, contribution stance, security note (no unsafe eval of untrusted configs), professional docs.

10. **Simulation only**  
    Never claim flight-critical software. HIL is a *test harness* for integration learning, not a certification path.

11. **SIL first; HIL-ready seams**  
    Default design loop is in-process SIL. Architecture separates **control laws** from **plant I/O** and **transport adapters** so HIL can attach later without a second sim stack (see `docs/ARCHITECTURE.md` §7A).

### 7.1 Logical modules (illustrative)

```
quadrotor-sim/
  docs/                 # architecture, theory notes (SPEC may live at repo root)
  configs/
    vehicles/
    controllers/
    missions/           # what to fly (waypoints, geometric params, …)
    studies/            # composes vehicle + controller + guidance + MC
  src/uavsim/           # layout normative in docs/ARCHITECTURE.md
    vehicles/           # params, limits, factory
    dynamics/           # f(x,u,p), linearize
    reference/          # ReferenceTrajectory, evaluate, feasibility
    guidance/           # planners only (waypoints, …)
    control/
    sim/
    studies/            # nominal pipeline orchestration
    metrics/
    monte_carlo/
    results/
    viz/
    cli/
  containers/
  tests/
```

### 7.2 Data flow (core)

```
Study config
    → load vehicle + controller + mission/guidance config
    → guidance.plan → reference trajectory (+ feasibility)
    → nominal closed-loop sim
         (optional) guidance.update / replan hooks for post-core backends
    → optional MC (local parallel and/or sharded workers)
    → write run artifacts + manifest (+ assembled MC summary)
    → (optional) viz / report / gallery stage
```

### 7.3 Results pipeline (intent)

**Do redesign; do not port the ME590 paper-output tangle.**

Minimum run directory contract (refine schema in architecture / results design):

```
runs/<study_id>_<timestamp>/
  manifest.yaml          # seeds, versions, hashes, worker topology
  study_config.yaml      # frozen copy
  guidance/              # backend id, mission snapshot, feasibility
  reference/             # generated reference artifacts (backend-agnostic)
  nominal/
    timeseries.*         # states, controls
    metrics.json
  monte_carlo/           # if requested
    trials.*             # tabular metrics per trial
    summary.json
    shards/              # optional intermediate shard outputs
  reports/
    summary.md
  figures/               # optional second stage
```

Machine-readable first; pretty plots second.

### 7.4 Systems / orchestration (core intent)

| Mode | Intent |
|------|--------|
| Local | Dev loop: single sim, small MC, process pool |
| Container single | Same study inside image; demo / CI parity |
| Sharded workers | Partition MC trial indices; workers write shard artifacts; coordinator merges summary + full trial table |

Coordinator must be deterministic given seed + trial index mapping. Failure of a shard must be visible in the manifest (partial vs failed study policy: document at implementation; default **fail the study** if any required shard fails).

### 7.5 Guidance extensibility (architecture contract)

The architecture document **must** specify:

1. **Reference trajectory contract** — fields, evaluation API (`ref.at(t)` / equivalent), units/frames, required vs optional derivatives  
2. **Guidance backend protocol** — inputs (mission config, vehicle limits, optional world model), outputs (reference + metadata), error model  
3. **Mission config polymorphism** — study YAML selects `guidance: { type: waypoints | …, ... }` without a single flat waypoint-only schema forever  
4. **Sim integration points** — pre-sim plan only (core) vs optional per-step/per-event `update` for online nav (post-core, but hook reserved)  
5. **Feasibility** — runs on references; backend-specific checks may attach extra diagnostics  
6. **MC interaction** — which parameters perturb plant vs guidance; whether replan uses trial RNG  
7. **How to add a backend** — checklist in docs (mirror “how to add a controller”)

Core may implement only the waypoint family; reviews should reject designs that bake min-snap or `.wpt` types into `sim/` or `control/` internals.

---

## 8. Non-functional requirements

| ID | Area | Guidance |
|----|------|----------|
| N1 | Platform | Primary dev/runtime: **WSL2 Linux** at `~/proj/quadrotor-sim` |
| N2 | Reproducibility | Seeded RNGs; locked dependency set; manifest per run |
| N3 | Performance | Interactive single sims in seconds; MC scales via local pool and container shards |
| N4 | Quality | Unit + integration tests in CI; smoke study + container path smoke in CI when practical |
| N5 | UX | One README path: clone → install → first plot/study; CLI is `uavsim` |
| N6 | Docs | Theory brief + architecture + API; no undocumented magic numbers |
| N7 | Licensing | **MIT** |
| N8 | Safety messaging | Simulation only; not flight-critical software |
| N9 | Polyglot build | Documented how to build optional non-Python components; default path works without them until a hotspot ships |

---

## 9. Technology direction

**Binding leanings** for stand-up (architecture may refine versions and package names, not the overall posture).

| Concern | Direction | Notes |
|---------|-----------|-------|
| Public CLI / glue | **Python 3.11+** | Product name `uavsim` |
| Numerics (default) | NumPy / SciPy | ODE, linalg, optimize |
| LQR | SciPy and/or python-control | Prefer well-tested libs |
| Min-snap QP | **Open** — SciPy vs OSQP/cvxpy vs CasADi | CasADi is a natural polyglot/GNC-adjacent option |
| Config | Pydantic + YAML (or TOML) | Schema validation |
| Data | JSON metrics + columnar timeseries (**format open**: Parquet preferred lean) | Fast MC analytics |
| Viz | Matplotlib (static); optional Plotly (interactive HTML) | Results consumers only; see §11A |
| Local parallel | joblib / multiprocessing / concurrent.futures | Local MC |
| Containers | Docker + Compose | Single-study and worker shards |
| Orchestration | Compose scale-out first; queue optional (Could) | Core needs shards + assemble |
| Packaging | `uv` + `pyproject.toml` preferred | Modern Python ops |
| CI | GitHub Actions | test + lint + small study (+ container smoke when ready) |
| License | MIT | |
| Polyglot | Explicit package/FFI boundary | First hotspot chosen when justified by min-snap, speed, or demo story |

---

## 10. Monte Carlo specification (core behavior)

### 10.1 Purpose

Quantify closed-loop tracking degradation under parametric uncertainty typical of mass properties and geometry — including at **portfolio scale** via sharded workers.

### 10.2 Default uncertainty model (heritage-inspired, tunable)

| Parameter | Distribution (default idea) | Notes |
|-----------|-----------------------------|-------|
| mass `m` | Normal, relative σ ~ 5% | Clamp to physical positivity |
| inertias | Normal, relative σ ~ 7.5% | Keep positive definite / positive diagonals |
| arm length `L` | Normal, absolute or relative small σ | If used by allocation later; plant may only need I,m today |

Exact distributions live in study config. Controller may be designed on **nominal** parameters while plant uses **perturbed** parameters (heritage behavior)—document this assumption; make “redesign K per trial” an optional mode.

### 10.3 Outputs

- Per-trial metrics table (complete after shard merge)
- Summary statistics (mean, std, quantiles, failure rate)
- Correlation of parameters vs tracking error
- Optional plots: histograms/CDFs, scatter sensitivity, boxplots
- Manifest entries for seed, trial count, shard map, worker image identity

### 10.4 Sharding rules (intent)

- Trial `i` is a pure function of `(base_seed, i, study_config, code_identity)` for RNG streams
- Shards are disjoint index ranges covering `0..N-1`
- Merge is order-independent for the trial table; summary is computed on the merged table

---

## 11. Metrics (core set)

### Tracking

- RMSE position (overall and per-axis)
- Max position error; final position error
- Time-in-bounds (%), configurable tolerance
- RMSE attitude; max |roll|, |pitch|, |yaw|
- RMSE velocity; max speed

### Control

- Integrated effort proxy (document units/limitations)
- Saturation fraction for thrust and torques
- Peak controls

### Success

Define explicit boolean criteria, e.g.:

- Completes full horizon without NaN/Inf
- Max position error below threshold
- Attitudes remain within configured envelope

Exact thresholds are config, not buried constants without names.

---

## 11A. Visualization pack (Should — portfolio analysis UX)

**Hard rule:** all viz is a **consumer of run directories** (and optional controller artifacts). No imports from live `sim` loop state. Frames: paths plotted as NED with **up = −D** for human readability; vector math remains NED/body as documented on each figure.

### 11A.1 Capability list (V1–V8)

| ID | Capability | Acceptance |
|----|------------|------------|
| **V1** | **Playback + path trail** | Interactive view: play/pause/scrub; flown path trail; reference path when `reference/grid.npz` exists |
| **V2** | **Dual-run 3D overlay** | `compare` (or report dual) shows two trails / vehicle markers; same alignment policy as S10 |
| **V3** | **Time-synced strip charts** | Position error, controls \(u(t)\), attitude vs \(t\) — static pack always; optional synced panel in interactive HTML |
| **V4** | **Saturation / limit shading** | Control time series mark samples near thrust/torque limits (from vehicle limits in study config or controller artifact) |
| **V5** | **MC plot pack** | When `trials.csv` present: RMSE hist + CDF; **all param scatters** vs RMSE (mass, inertias, arm); multipanel sensitivity; **metric boxplots** + multi-metric hist grid; success bar; correlation bars; **exemplar path overlay** (re-sim best/median/worst); interactive `mc_dashboard.html` / `mc_sensitivity.html` with `--interactive` |
| **V6** | **Feasibility callouts** | Report header/section from `guidance/feasibility.json` (ok, issue codes, severities) |
| **V7** | **Interview one-liner** | `uavsim report <run> --interactive` writes interactive HTML under `figures/` and prints the path |
| **V8** | **Export stills** | At least one PNG keyframe of the 3D scene (path + vehicle pose) for README / static sharing |

### 11A.2 Interactive 3D vectors (single-run view)

At current time \(t\), draw (relative length for comparison; **absolute values in HUD**):

| Vector | Encoding |
|--------|----------|
| Velocity \(v\) (NED) | Arrow at vehicle |
| Position error \(p - p_\mathrm{ref}\) | Arrow (when reference available) |
| Thrust direction | Along −body-\(z\), length ∝ \(F\) or \(F/(mg)\) |
| Body axes triad | Unit length (frame literacy) |
| Optional: \(\omega\), \(\tau\) | Body frame or HUD-only if cluttered |

HUD (absolute): \(t\), \(\|e_p\|\), \(\|v\|\), \(F\), \(\|\tau\|\), Euler (deg), success/in-bounds if metrics present.

### 11A.3 CLI / artifacts

```bash
uavsim report runs/<id>                 # markdown + static figures (V3–V6, V8)
uavsim report runs/<id> --interactive   # + Plotly HTML (V1, V7); requires viz extra
uavsim compare runs/a runs/b            # deltas + overlays; --interactive → dual 3D (V2)
```

Outputs under `runs/.../figures/` (and compare output dir): `*.png`, `flight_3d.html`, optional `compare_3d.html`.

### 11A.4 Dependencies

- **Must path:** matplotlib (static) via optional `viz` / `dev` extra (CI uses `dev`).
- **Interactive:** plotly in `viz` extra; missing plotly → clear message, static pack still works.

---

## 12. Trajectory feasibility (core policy)

Pre-simulation checks should report at least:

| Check | Intent |
|-------|--------|
| Peak attitude demand | Linearization / small-angle honesty |
| Peak / RMS yaw rate | Actuator & tracking realism |
| Peak yaw acceleration | Torque authority `τ_max / I_zz` class limits |
| Peak horizontal accel / velocity | Optional aggressiveness flags |

Policy: **warn by default, optionally fail the study** when critical limits exceeded. Feasibility results must appear in the run artifacts.

---

## 13. CLI / user journeys (target UX)

Product CLI name: **`uavsim`**.

```bash
# environment
uv sync   # or: docker build …

# --- SIL design loop ---
uavsim simulate configs/studies/hover_nominal.yaml
uavsim study configs/studies/square_mc.yaml
uavsim study configs/studies/square_mc.yaml --backend docker --shards 8

# export designed controller (Should → Must before serious HIL)
uavsim export-controller runs/<sil_id> --out artifacts/controllers/lqr_hover_v1.yaml

# post-process / viz
uavsim report runs/<id> --figures

# compare two SIL runs or SIL vs HIL (multi-run viz)
uavsim compare runs/<sil_id> runs/<hil_or_other_id> --figures

# compare controllers (Should)
uavsim study configs/studies/compare_lqr_vs_alt.yaml

# --- HIL (post-core) ---
# uavsim hil configs/studies/hover_nominal.yaml --transport udp --endpoint …

# future: non-waypoint guidance
# uavsim simulate configs/studies/helix_geometric.yaml
```

First-run experience must not require reading the ME590 MATLAB tree.

---

## 14. Testing strategy

Aligned with `GROK.md`: unit + integration; TDD default for new behavior; soft goldens only.

| Layer | Examples |
|-------|----------|
| Unit | Rotation conventions, hover trim force `≈ m g`, LQR poles stable, waypoint schema validation |
| Trajectory / guidance | Waypoint satisfaction (interp); min-snap smoke; feasibility on known bad auto-yaw cases; **reference contract tests independent of backend** |
| Closed-loop | Hover holds; gentle square tracks within loose bounds |
| Controller interface | LQR and alternate both satisfy protocol; comparison study smoke |
| Guidance interface | Mock/non-waypoint stub backend can drive sim without code changes in control/metrics (architecture-level acceptance) |
| MC | Seed reproducibility; N=2 smoke; summary schema stable |
| Systems | Shard merge correctness; container entrypoint smoke (CI or nightly if slow) |
| Golden (soft) | Optional reference metrics bands — **not** MATLAB bit parity |

Prefer **property / invariant tests** over fragile golden binaries.

---

## 15. Documentation plan (public)

1. **README** — value prop, quickstart, example figures, MIT, citations  
2. **Architecture** — modules, data flow, extension points, polyglot boundaries, orchestration  
3. **Theory notes** — NED, linearization assumptions, LQR, min-snap pointer to Mellinger & Kumar  
4. **Study authoring** — vehicle/controller/mission/MC configs  
5. **Results schema** — artifact contract  
6. **Roadmap** — deferred GNC capabilities  
7. **Containers / workers** — how to run single-image and sharded studies  

Narrative should credit ME590 research origins **without** requiring private Drive assets.

---

## 16. Portfolio / demo narrative

Positioning themes the project must make obvious:

1. **Flight dynamics literacy** — frames, underactuation, saturation  
2. **Control design** — LQR synthesis, weights as engineering knobs  
3. **Guidance / navigation** — pluggable reference generation; waypoints + min-snap first; room to grow beyond  
4. **Uncertainty quantification** — MC robustness, not single-run demos only  
5. **Software systems for GNC** — configs, artifacts, CI, **containers, sharded workers**  
6. **Extensibility** — second controller + second guidance family path + polyglot-ready boundaries  

**Core demo scripts (target):**

- Clone → `uavsim simulate` gentle mission → plots/metrics  
- `uavsim study` MC with seed reproducibility  
- Same study with `--backend docker --shards N` → identical summary within numerical tolerance  
- (Should) Two controllers on one mission; **export** + **compare** two SIL runs  
- (Post-core) HIL session compared to SIL baseline with `uavsim compare`  

---

## 17. Acceptance criteria for “core complete”

Core is complete when all of the following hold:

**GNC SIL (epics A–C)**

1. Clone → install → run documented nominal sim and MC smoke on WSL without tribal knowledge  
2. LQR closed-loop tracks a gentle mission with metrics written to a run directory  
3. MC study produces trial table + summary + manifest with fixed seed reproducibility  
4. Feasibility warnings appear for a known aggressive auto-yaw case  
5. Tests and lint pass in CI; small MC smoke runs in CI  

**Systems (epic F)**

6. **Container image** runs a documented study  
7. **Sharded MC path** produces assembled summary consistent with local MC for a fixed seed/N (documented tolerance)  

**Extensibility & workflow readiness (epics B, D, E design)**

8. README + architecture docs explain how to add a **controller**, a **guidance backend**, and (at design level) a non-Python module  
9. Architecture (and ideally a stub/test) proves sim/control/metrics do not hard-depend on waypoint/min-snap types  
10. **Should:** second controller + comparison example study  
11. **Should:** controller **export** artifact round-trip (US-D1 / S9)  
12. **Should:** **`uavsim compare`** on two SIL runs produces metric deltas + at least one overlay figure (US-E3 / S10)  
13. **Should:** plant integration uses a separable command source (SIL adapter) so HIL is not a rewrite (S11)  

**Hygiene**

14. No dependency on the MATLAB tree at runtime  
15. MIT license file present; safety messaging (simulation only) in README  

**Explicitly not required for core complete:** live HIL hardware, firmware flash, certified software claims.

Refinement of numerics and exact orchestration tooling is expected during implementation; this SPEC is the living product contract, not a frozen ICD.

---

## 18. Open decisions (remaining)

| Topic | Options / notes |
|-------|-----------------|
| Min-snap solver stack | SciPy vs OSQP/cvxpy vs CasADi (polyglot/GNC story) |
| Timeseries format | Parquet (lean) vs HDF5 vs NPZ |
| First polyglot hotspot | None until needed vs CasADi min-snap vs compiled dynamics |
| Alternate controller type | PID cascade vs geometric |
| First post-core guidance mode | Geometric paths vs corridor/MPC vs map-aware vs replan demo — **pick when roadmap prioritizes** |
| Online guidance in sim | Reserve hook only vs implement minimal replan smoke in a late phase |
| Compose vs other worker driver | Docker Compose first lean; k8s out of scope |
| Remote origin | **Closed:** `git@github.com:trey-copeland/uavsim.git` (public timing still open if desired) |
| Package import name | **Closed lean:** `uavsim` (see ARCH); revisit only if packaging forces rename |
| SPEC home | **Root `SPEC.md`** for now (with `docs/ARCHITECTURE.md`) |

---

## 19. Implementation phases (guidance)

**Living checklist and now/next/later:** [`ROADMAP.md`](ROADMAP.md).

Phases are sequential **capability gates**, not strict calendar. Systems work is **pulled forward** relative to v0 (not left as Phase 4 garnish). Phases map to user-story epics (A–F).

### Phase 0 — Stand-up
- Repo skeleton, packaging (`uv`/`pyproject`), lint, test harness, CI stub  
- Docs already: SPEC + ARCH (keep in sync as code lands)  

### Phase 1 — Vehicle, dynamics, SIL loop (epics A, C partial)
- `vehicles` + `dynamics` + LQR + trivial `reference` + `studies` pipeline  
- Separable plant step + in-process SIL adapter (S11 foundation)  
- Metrics + run artifacts + `uavsim simulate`  

### Phase 2 — Guidance + controller interface (epics B, C)
- Waypoint load + interp + min-snap + feasibility  
- Guidance registry; stub backend test  
- Controller protocol hardened; start alternate controller (S6)  

### Phase 3 — Robustness, results, local MC (epics C, F partial)
- MC engine, summaries, plots-as-consumer (single-run `report`)  
- `uavsim study`; seed reproducibility  

### Phase 4 — Systems core (epic F)
- Container image + one-command study  
- Sharded workers + assemble  
- CI smoke as practical  

### Phase 5 — Workflow polish toward HIL readiness (epics D, E-SIL)
- Controller **export** + SIL round-trip (S9)  
- Multi-run **`compare`** for two SIL runs (S10); multi-run viz APIs (S5a)  
- Controller comparison study if not done  
- README figures / gallery (Should)  

### Phase 5b — Visualization pack (S5 / S5b / §11A)
- V1–V8: interactive 3D, dual overlay, strips, saturation, MC plots, feasibility, CLI, stills  
- `uavsim report --interactive`; compare dual HTML when plotly available  

### Phase 6 — Navigation expansion (post-core; epic B growth)
- First non-waypoint guidance backend and/or replan demo  

### Phase 7 — HIL/PIL (post-core; epic E)
- Fixed-step plant + full plant I/O schemas (C6)  
- First transport adapter + timeouts (C7)  
- SIL vs HIL via export + `compare` (C8)  
- Safety messaging: harness only  

---

## 20. References (domain)

- Anderson & Moore — Linear Quadratic methods  
- Bouabdallah — quadrotor design and control literature  
- Mellinger & Kumar (2011) — minimum-snap trajectory generation  
- ME590 project materials (private heritage; domain reference only; **cite, do not vendor**)  

---

## 21. Change log

| Version | Date | Notes |
|---------|------|-------|
| v0 | 2026-07-16 | Initial core SPEC from ME590 capability capture + redesign intent; WSL project root `~/proj/quadrotor-sim` |
| v0.1 | 2026-07-18 | SPEC refinement: systems-heavy core (containers + sharded MC as Must); Python-first + day-one polyglot boundaries; CLI `uavsim`; MIT; cite-only paper; second controller elevated to Should; closed decisions table; phases reordered; remaining opens narrowed; aligned with `GROK.md` GSD |
| v0.1.1 | 2026-07-18 | Guidance/navigation extensibility: pluggable guidance beyond waypoints→min-snap; mission vs backend vs reference trajectory; §7.5 architecture contract; deferred nav modes listed; F2a/S3a/C5; acceptance + phases updated |
| v0.1.2 | 2026-07-18 | Linked `docs/ARCHITECTURE.md`; closed package name lean `uavsim` and root SPEC home |
| v0.1.3 | 2026-07-18 | Aligned logical modules with ARCH v0.1: `reference`/`guidance`, vehicles vs dynamics, `missions` + `studies` configs |
| v0.1.4 | 2026-07-18 | HIL-ready architecture intent: SIL-first; plant I/O vs control-law seams; C6–C7; Phase 7; principle §7.11 |
| v0.1.5 | 2026-07-18 | Primary workflow §1.3; user stories §1.4 (epics A–F); export/compare CLI; S5a/C8/C9 |
| v0.2 | 2026-07-18 | Refined expectations §1.3.1; closed decisions for layout/workflow/export/compare; S9–S11; phased epic map; core acceptance includes export + multi-run compare Shoulds |
| v0.2.1 | 2026-07-18 | Link `ROADMAP.md` as sequencing home; §19 points to roadmap |
| v0.2.2 | 2026-07-19 | §11A visualization pack V1–V8; S5b interactive 3D; Phase 5b |

---

*This document freezes product intent before code: what we are building, what we refuse to carry forward, and how the public GNC + systems story should read. Implementation layout belongs in the architecture document.*
