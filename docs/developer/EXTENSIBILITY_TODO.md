# Extensibility backlog

Concrete **TODOs** so research users know what works **today** vs what needs product work.  
Update this file when hooks land; keep linked guides in sync.

Legend: **Done** · **Partial** · **TODO** · **Out of scope (core)**

---

## Vehicles

| ID | Item | Status | Notes |
|----|------|--------|-------|
| V-1 | YAML vehicle definition + study path | **Done** | `configs/vehicles/`, `VehicleParams` |
| V-2 | Shared params for plant / control / MC | **Done** | |
| V-3 | Diagonal inertia only | **Partial** | Off-diagonal products **TODO** |
| V-4 | Optional aero / drag coefficients on vehicle schema | **TODO** | Blocked by `extra="forbid"` until fields added |
| V-5 | Enforce \(F_\max \ge mg\) at validate | **TODO** | Soft expectation today |
| V-6 | Motor mixer uses `arm_length_m` | **Done** | X-quad allocation in `dynamics/mixer.py` |
| V-7 | Arm mechanics / elasticity params | **TODO** | Parametric + lumped states |
| V-8 | Multi-airframe families (tilt-rotor, hybrid VTOL, etc.) | **TODO** (low priority) | Pluggable dynamics + extended `VehicleParams` / mixer; preserve core 6-DoF base. Guide: [airframes.md](airframes.md) |

Guide: [vehicles.md](vehicles.md) · [airframes.md](airframes.md)

---

## Control

| ID | Item | Status | Notes |
|----|------|--------|-------|
| C-1 | `Controller` protocol | **Done** | |
| C-2 | LQR hover design + study config | **Done** | |
| C-3 | PID cascade + study config | **Done** | |
| C-4 | Factory from study `controller.type` | **Done** | Manual branches |
| C-5 | Controller **registry** (like guidance) | **TODO** | Reduce pipeline/factory edits |
| C-6 | Export / load for LQR + PID | **Done** | |
| C-7 | Export for arbitrary new laws | **Partial** | Must extend export module |
| C-8 | Geometric / SE(3) controller | **TODO** | |
| C-9 | Partial-state / noisy measurements | **Done** | Noise + `channels` selection / \(H\); richer IMU physics still open |
| C-10 | Entry-point plugins for third-party laws | **TODO** | |
| C-11 | Control from state estimate (not only x_true) | **Done** | Closed-loop: plant → measure → observer → controller |

Guide: [control.md](control.md)

---

## Estimation / observers (Phase 5d)

| ID | Item | Status | Notes |
|----|------|--------|-------|
| EST-1 | Configurable measurement models (noise) | **Done** | Full or partial channels; `Observation` + H |
| EST-2 | `StateObserver` protocol (predict / update) | **Done** | Wired in closed-loop |
| EST-3 | Reference filter implementation | **Done** | `linear_kf` (hover A,B) + `mekf` (error-state / multiplicative att) |
| EST-4 | Study config `sim.observer` | **Done** | `none` \| `linear_kf` \| `mekf`; `channels` list |
| EST-5 | Log `x_hat` in run artifacts | **Done** | `nominal/timeseries.npz` key `x_hat` |

Demos: `figure_eight_observer.yaml`, `figure_eight_mekf.yaml` (partial `pos`+`omega`).

---

## Guidance & navigation

| ID | Item | Status | Notes |
|----|------|--------|-------|
| G-1 | Hold backend | **Done** | |
| G-2 | Waypoints + interp / minsnap / auto | **Done** | |
| G-3 | `register_guidance` registry | **Done** | |
| G-4 | Study config open to registered backends only via registry | **Partial** | Pipeline **hard-codes** hold/waypoints |
| G-5 | Drive `_build_guidance` from registry + pydantic plugins | **TODO** | High leverage |
| G-6 | `guidance.update` in closed-loop sim | **TODO** | Protocol only |
| G-7 | First non-waypoint backend (geometric) | **TODO** | Phase 6 |
| G-8 | Multi-segment / mixed backends | **TODO** | |
| G-9 | Swappable min-snap QP (CasADi/OSQP) | **TODO** | Boundary ready |

Guide: [guidance.md](guidance.md)

---

## Dynamics / plant

| ID | Item | Status | Notes |
|----|------|--------|-------|
| D-1 | Nonlinear 6DOF body-wrench plant | **Done** | Euler default + optional quat plant; no drag |
| D-2 | Hover analytic linearization for LQR | **Done** | Small-angle; revisit with D-10 |
| D-3 | `DynamicsModel` protocol + plant injection | **Done** | `dynamics/model.py`; `SimPlant(dynamics=…)` / `get_dynamics_model` |
| D-4 | Vehicle aero params (drag, damping) | **TODO** | Plan D1 |
| D-5 | Drag / damping in \(f(x,u,p)\) | **TODO** | Plan D3 |
| D-6 | Numeric linearization utility | **TODO** | |
| D-7 | Motor/prop first-order states | **Done** | `sim.plant: motors`; +4 ω states; `dynamics/motors.py` |
| D-8 | Control allocation / mixer | **Done** | X-quad wrench ↔ forces; `dynamics/mixer.py` |
| D-9 | Wind / process disturbance API | **TODO** | |
| D-10 | Quaternion (SO(3)) attitude + error-state control path | **Done** | Plant + SO(3) control/metrics + aggressive demo. Native 13-state export optional polish |
| D-11 | HIL validation seams + companion project | **TODO** | Fixed-step, I/O; parallel with rig build (do not block 5c) |
| D-12 | Multi-airframe dynamics extensions | **TODO** | Tilt mechanisms, mode transitions, hybrid aero (after mixer) |
| D-13 | Flexible / elastic body (lumped modes) | **TODO** | After D-3 (+ ideally D-10); extends V-7 into plant states |

Guide: [dynamics.md](dynamics.md) · [airframes.md](airframes.md) · ROADMAP Phase 5c

---

## Studies / MC / systems (related)

| ID | Item | Status | Notes |
|----|------|--------|-------|
| S-1 | Study composes vehicle + controller + guidance | **Done** | |
| S-2 | MC param perturbation of vehicle | **Done** | mass/I/arm |
| S-3 | MC redesign non-LQR controllers | **Partial** | Factory re-run; validate per law |
| S-4 | Study-selected dynamics backend | **Partial** | `sim.attitude: euler\|quat` wired; arbitrary named `dynamics.type` still open |
| S-7 | Airframe selector in studies + MC perturbations | **TODO** | Comparative robustness (e.g. quad vs tilt-rotor) |

---

## Comms & instrumentation

Hardware and transport live primarily in a **HIL companion** project; this backlog tracks the seams `uavsim` must stay ready for.

| ID | Item | Status | Notes |
|----|------|--------|-------|
| COMM-1 | NATS/MQTT for rig (myDAQ ↔ React) | **TODO** | Lightweight pub/sub on the lab rig |
| COMM-2 | DDS/CAN for flight system | **TODO** | Future-proof layering beyond lab bus |
| INSTR-1 | High-bandwidth accels (>1 kHz) + ESC RPM | **TODO** | e.g. ICM-42688 / ADXL + myDAQ |

---

## Suggested implementation order

**SIL (Track A — do now while HIL rig is ordered/built):**

1. ~~**D-10 / 5c**~~ — **Done** (quat plant, SO(3) control, aggressive F8, `DynamicsModel`).  
2. ~~**Phase 5d observers**~~ — **Done** (EST-1…5, C-9/C-11: `linear_kf` / `mekf`, channels, `x_hat`).  
3. ~~**D-7 + D-8**~~ — **Done** (mixer + first-order motors; `sim.plant: motors`).  
4. **D-13 / V-7** — flexible / elastic lumped states ← **Now** (or drag D-4/D-5).  
5. **D-4/D-5** — drag/aero as needed.  
6. **G-5 / C-5** — registries when plugin ergonomics block experiments.  
7. **V-8 / D-12 / S-7** — multi-airframe families after mixer + protocol.

**HIL rig (Track B — parallel, long lead; software when hardware exists):**

1. Order/build frame, myDAQ, high-rate sensors, ESCs (INSTR-1).  
2. Thin **D-11** fixed-step / I/O seams in this repo.  
3. Companion: NATS/MQTT + dashboard (COMM-1); DDS/CAN later (COMM-2).  
4. Phase 7 transport + SIL↔HIL compare (**uses 5d observer path**).

Do **not** block SIL plant work on the rig. Prefer finishing motors/mixer (and observers already shipped) before claiming HIL-ready control.

---

## Vision note (2026-07)

Design extensions so we can grow **mission envelope** (quaternions), **plant fidelity** (motors, flex), and **HIL** without breaking:

- default quadrotor SIL demos and showcase regression  
- Monte Carlo / export / compare  
- viz consumers (schema-versioned timeseries)  

Document airframe families in [`airframes.md`](airframes.md) as prototypes land.

---

## How to use this backlog

- **Users:** If your experiment is marked **TODO**, plan a small design note + PR against the IDs above rather than silent core hacks.  
- **Maintainers:** When closing a TODO, flip status here and add a short “as of \<date\>” example in the matching guide.  
- **Agents:** Prefer implementing the highest-leverage **TODO** over one-off forks when the user asks for extensibility.
