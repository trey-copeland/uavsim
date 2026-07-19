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

Guide: [vehicles.md](vehicles.md)

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
| D-3 | `DynamicsModel` protocol + plant injection | **TODO** | See dynamics.md plan D2 |
| D-4 | Vehicle aero params (drag, damping) | **TODO** | Plan D1 |
| D-5 | Drag / damping in \(f(x,u,p)\) | **TODO** | Plan D3 |
| D-6 | Numeric linearization utility | **TODO** | |
| D-7 | Motor/prop first-order states | **TODO** | Changes state dim |
| D-8 | Control allocation / mixer | **TODO** | |
| D-9 | Wind / process disturbance API | **TODO** | |

Guide: [dynamics.md](dynamics.md)

---

## Studies / MC / systems (related)

| ID | Item | Status | Notes |
|----|------|--------|-------|
| S-1 | Study composes vehicle + controller + guidance | **Done** | |
| S-2 | MC param perturbation of vehicle | **Done** | mass/I/arm |
| S-3 | MC redesign non-LQR controllers | **Partial** | Factory re-run; validate per law |
| S-4 | Study-selected dynamics backend | **TODO** | Depends on D-3 |

---

## Suggested implementation order (if enabling research extensions)

1. **G-5** — registry-driven guidance in pipeline (unblocks nav experiments without core edits).  
2. **C-5** — controller registry (same pattern).  
3. **D-3 + D-1/D-4/D-5** — pluggable dynamics + drag params (the usual research ask).  
4. **G-6** — online `update` hook in sim (replan / reactive nav).  
5. **D-8** — mixer if motor-level studies matter.

---

## How to use this backlog

- **Users:** If your experiment is marked **TODO**, plan a small design note + PR against the IDs above rather than silent core hacks.  
- **Maintainers:** When closing a TODO, flip status here and add a short “as of \<date\>” example in the matching guide.  
- **Agents:** Prefer implementing the highest-leverage **TODO** over one-off forks when the user asks for extensibility.
