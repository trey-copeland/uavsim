# Dynamics: model today and how to extend it

**Package:** `uavsim.dynamics`  
**Core EOM:** `dynamics/nonlinear.py` → `state_derivative(x, u, vehicle)`  
**Linearization:** `dynamics/linearize.py` → `hover_linearization(vehicle)` for LQR  
**Plant:** `sim/plant.py` → `SimPlant` calls `state_derivative` each step  

---

## Model today (what is implemented)

Rigid-body 6DOF quadrotor, **no aerodynamic drag**, **no propeller lag**, **body wrench control**, **ZYX Euler** attitude.

### State and control

| | |
|--|--|
| \(x \in \mathbb{R}^{12}\) | NED position, ZYX Euler, NED velocity, body rates |
| \(u \in \mathbb{R}^{4}\) | \([F, \tau_\phi, \tau_\theta, \tau_\psi]\) |
| Thrust | Force along **−body-\(z\)**, rotated to NED |
| Gravity | \(+mg\) along NED \(+z\) (down) |
| Inertia | Diagonal `Ixx, Iyy, Izz` from vehicle |
| Torque eq. | \(I\dot\omega = \tau - \omega \times I\omega\) |

### Planned next (Phase 5c — ROADMAP)

While the HIL test rig is ordered/built, SIL priority is **attitude representation + plant plug points**, not waiting on hardware:

| ID | Change | Why |
|----|--------|-----|
| **D-10** | Quaternion (SO(3)) kinematics + error-state control/metrics | Large-attitude / aggressive missions without Euler singularities |
| **D-3** | `DynamicsModel` protocol | Motors, flex, airframes as additive plants |
| **D-7/D-8** then **D-13** | Motors/mixer → flexible/elastic states | Fidelity for later HIL; model in SIL first |

Gentle figure-eight / square demos remain valid regression under Euler until 5c lands and soft goldens are rebaselined.

### Phase 5c.1 status (plant kinematics — landed)

| Item | API |
|------|-----|
| Euler plant (default) | `state_derivative` — \(x \in \mathbb{R}^{12}\) |
| Quaternion plant | `state_derivative_quat` — \(x \in \mathbb{R}^{13}\): pos, \(q_wxyz\), vel, \(\omega\) |
| Renorm after steps | `renormalize_quat_state` (also used by `integrate_fixed_step(..., attitude="quat")`) |
| Layout bridges | `euler_state_to_quat_state` / `quat_state_to_euler_state` |
| Convention | Scalar-first unit quat; \(R_{b\to i}(q)\); \( \dot q = \tfrac12 q \otimes [0,\omega] \) |

**Not yet:** closed-loop / LQR / study pipeline still use the Euler 12-state path (5c.2+).

### Where it is used

```text
Controller.compute → ActuatorCommand u
       ↓
SimPlant.step / closed_loop RHS
       ↓
state_derivative(x, u, vehicle) → xdot
```

Saturation uses `vehicle.limits` before / around integration (see plant + closed loop).

### Hover linearization (LQR only)

`hover_linearization` builds \(A,B\) about hover / small angle:

- \(\ddot N \approx -g\,\theta\), \(\ddot E \approx +g\,\phi\)
- Thrust column on vertical channel; torque columns on rates

If you change nonlinear \(f\), **you must revisit** linearization or LQR will not match the plant.

---

## What you can do without new architecture

### 1. Change mass / inertia / \(g\) only

Edit the **vehicle YAML** — dynamics already read `vehicle.mass_kg`, inertia, `gravity_m_s2`. No code change.

### 2. Patch drag inside `state_derivative` (local experiment)

Small research fork: add velocity-dependent force in the acceleration block:

```python
# Conceptual — not in mainline
# NED drag opposing velocity (very simplified)
k_lin = getattr(vehicle, "drag_lin", 0.0)  # would need vehicle schema field
f_drag_i = -k_lin * v
a = (f_thrust_i + f_grav + f_drag_i) / m
```

**Problems with doing only this:**

- `VehicleParams` has `extra="forbid"` → cannot pass `drag_lin` via YAML until schema grows.
- LQR design ignores drag → closed-loop may still work but is mismatched.
- MC / export / docs will not know about the coefficient.

Treat as a **spike**; for product-quality drag, follow the plan below.

### 3. Open-loop / unit tests of \(f\)

```python
from uavsim.dynamics import state_derivative
from uavsim.vehicles.params import default_vehicle
import numpy as np

v = default_vehicle()
x = np.zeros(12)
u = v.u_hover()
xdot = state_derivative(x, u, v)
assert abs(xdot[8]) < 1e-9  # hover vertical accel ~ 0
```

---

## How we *should* extend dynamics (plan)

These are the **enablement steps** for research (drag, prop models, alternate 6DOF). Tracked in [EXTENSIBILITY_TODO.md](EXTENSIBILITY_TODO.md).

### Phase D1 — Vehicle aero / param bag (schema)

- Extend `VehicleParams` (or nested `aero:`) with optional fields, e.g.  
  `drag_lin_ns_m`, `drag_quad_ns2_m2`, `c_mq` (pitch damping), etc.
- Keep defaults **zero** so existing studies bit-match.
- Document units in vehicle guide.

### Phase D2 — Dynamics backend protocol

Introduce a thin interface (names illustrative):

```text
DynamicsModel
  id: str
  state_dim / control_dim
  f(x, u, vehicle) -> xdot
  # optional:
  linearize(vehicle, x_eq, u_eq) -> A, B
```

- Default impl: current nonlinear + hover linearize.
- `SimPlant` takes `dynamics: DynamicsModel` (default legacy).
- Study config optional: `dynamics: { type: rigid_body_v1 | rigid_body_drag_v1 }`.

### Phase D3 — Drag / damping models

- Implement `f` terms: linear/quadratic translational drag in NED or body;  
  optional rotor-induced or rate damping on \(\omega\).
- Update or replace hover linearization (numerical finite-difference fallback is OK).
- Add unit tests: energy dissipation, hover trim still holds when \(v=0\).

### Phase D4 — Propeller / motor dynamics (optional)

- First-order lag on thrust or motor RPM states → **state dimension change**.
- Requires careful state layout docs + controller awareness (or outer wrench still commanded).
- Export / metrics state maps must version.

### Phase D5 — Control allocation

- Optional mixer: motors → \(u\) body wrench using `arm_length_m` and CT/CQ.
- Controllers may still output wrench; plant applies mixer + motor limits.

---

## Coupling table (if you change \(f\))

| Component | Action |
|-----------|--------|
| `state_derivative` | Your new physics |
| `hover_linearization` / LQR | Re-derive or numeric linearize |
| `pid_cascade` tilt map | Check small-angle thrust direction still consistent |
| Feasibility peak-tilt from accel | May still be valid; yaw limits independent |
| MC perturbations | Extend if new params should be uncertain |
| Controller export | Document plant assumptions / vehicle hash |
| Tests | Trim, free-fall, drag-on energy, regression hover |

---

## TODOs / gaps (dynamics) — summary

| Item | Status |
|------|--------|
| Translational drag (vehicle / prop) | **TODO** — not in \(f\) |
| Aero moments / rate damping | **TODO** |
| Dynamics pluggable backend | **TODO** — single global `state_derivative` |
| Numeric linearization helper | **TODO** |
| Motor/prop states | **TODO** |
| Mixer / allocation | **TODO** |
| Wind / disturbance injection | **TODO** (could be \(u\) or force in \(f\)) |

Until D2 exists, research drag work will require **editing core nonlinear.py** or a private fork path — call that out in papers/portfolio as non-upstream.
