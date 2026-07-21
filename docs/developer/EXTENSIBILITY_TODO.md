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
| V-6 | Motor mixer uses `arm_length_m` | **TODO** | Field stored unused by plant |
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
| C-9 | Partial-state / noisy measurements | **TODO** | Bus is ideal full state |
| C-10 | Entry-point plugins for third-party laws | **TODO** | |

Guide: [control.md](control.md)

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
| D-1 | Nonlinear 6DOF body-wrench plant | **Done** | No drag |
| D-2 | Hover analytic linearization for LQR | **Done** | |
| D-3 | `DynamicsModel` protocol + plant injection | **TODO** | High leverage for airframes; see dynamics.md plan D2 |
| D-4 | Vehicle aero params (drag, damping) | **TODO** | Plan D1 |
| D-5 | Drag / damping in \(f(x,u,p)\) | **TODO** | Plan D3 |
| D-6 | Numeric linearization utility | **TODO** | |
| D-7 | Motor/prop first-order states | **TODO** | Changes state dim; foundational for multi-airframe |
| D-8 | Control allocation / mixer | **TODO** | |
| D-9 | Wind / process disturbance API | **TODO** | |
| D-11 | HIL validation seams + companion project | **TODO** | Fixed-step, I/O contracts; hardware out of this repo |
| D-12 | Multi-airframe dynamics extensions | **TODO** | Tilt mechanisms, mode transitions, hybrid aero (additive to core) |

Guide: [dynamics.md](dynamics.md) · [airframes.md](airframes.md)

---

## Studies / MC / systems (related)

| ID | Item | Status | Notes |
|----|------|--------|-------|
| S-1 | Study composes vehicle + controller + guidance | **Done** | |
| S-2 | MC param perturbation of vehicle | **Done** | mass/I/arm |
| S-3 | MC redesign non-LQR controllers | **Partial** | Factory re-run; validate per law |
| S-4 | Study-selected dynamics backend | **TODO** | Depends on D-3 |
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

## Suggested implementation order (research enablement)

Prefer this order when prioritizing post-core / lab work (still subject to portfolio need):

1. **Motor dynamics + mixer** (D-7, D-8) — foundational for all airframes and motor-level studies.  
2. **Observer + high-speed sensors** (C-9, INSTR-1) — partial-state path; myDAQ integration in companion.  
3. **NATS rig comms + React dashboard** (COMM-1) — lab loop without pretending it is flight DDS.  
4. **HIL companion project seams** (D-11, ARCH §7A) — fixed-step plant + I/O contracts.  
5. **Multi-airframe extensions** (V-8, D-12, S-7) — tilt-rotor etc.; additive, no core refactor.  
6. **G-5 / C-5** — registry-driven guidance/control when experiments need zero pipeline edits.  
7. **D-3 + D-4/D-5** — pluggable dynamics + drag when plant variants are the research ask.

Earlier GSD enablement (registry + drag) remains valid when the ask is software plugins without hardware.

---

## Vision note (2026-07)

Design all extensions to support **heterogeneous airframes** and **HIL** without breaking:

- quadrotor core 6-DoF  
- Monte Carlo / export / compare  
- viz and showcase consumers  

Document airframe families in [`airframes.md`](airframes.md) as prototypes land.

---

## How to use this backlog

- **Users:** If your experiment is marked **TODO**, plan a small design note + PR against the IDs above rather than silent core hacks.  
- **Maintainers:** When closing a TODO, flip status here and add a short “as of \<date\>” example in the matching guide.  
- **Agents:** Prefer implementing the highest-leverage **TODO** over one-off forks when the user asks for extensibility.
