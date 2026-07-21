# Dynamics: model today and how to extend it

**Package:** `uavsim.dynamics`  
**Core EOM:** `dynamics/nonlinear.py` → `state_derivative` / `state_derivative_quat`  
**Linearization:** `dynamics/linearize.py` → `hover_linearization(vehicle)` for LQR  
**Protocol:** `dynamics/model.py` → `DynamicsModel` (`EulerRigidBodyDynamics`, `QuatRigidBodyDynamics`)  
**Plant:** `sim/plant.py` → `SimPlant` injects a `DynamicsModel` each step  

---

## Model today (what is implemented)

Rigid-body 6DOF quadrotor, **no aerodynamic drag**, **no propeller lag**, **body wrench control**. Attitude: **ZYX Euler** plant by default, or **unit-quaternion** plant via study config.

### State and control

| | |
|--|--|
| \(x \in \mathbb{R}^{12}\) (Euler, default) | NED position, ZYX Euler, NED velocity, body rates |
| \(x \in \mathbb{R}^{13}\) (quat plant) | NED position, unit quat \(q_{wxyz}\), NED velocity, body rates |
| \(u \in \mathbb{R}^{4}\) | \([F, \tau_\phi, \tau_\theta, \tau_\psi]\) |
| Thrust | Force along **−body-\(z\)**, rotated to NED |
| Gravity | \(+mg\) along NED \(+z\) (down) |
| Inertia | Diagonal `Ixx, Iyy, Izz` from vehicle |
| Torque eq. | \(I\dot\omega = \tau - \omega \times I\omega\) |

### Phase 5c — landed (attitude & plant seams)

| Item | Status / API |
|------|----------------|
| Euler plant (default) | `state_derivative` — \(x \in \mathbb{R}^{12}\) |
| Quaternion plant | `state_derivative_quat` — \(x \in \mathbb{R}^{13}\) |
| Renorm after steps | `renormalize_quat_state` |
| Layout bridges | `euler_state_to_quat_state` / `quat_state_to_euler_state` |
| Convention | Scalar-first unit quat; \(R_{b\to i}(q)\); \( \dot q = \tfrac12 q \otimes [0,\omega] \) |
| SO(3) attitude error | `dynamics/attitude_error.py` — LQR, PID, metrics |
| `DynamicsModel` (D-3) | `SimPlant(dynamics=…)` / `get_dynamics_model` |
| Study plant | `sim.attitude: euler` \| `quat` |
| Stress demo | `configs/studies/figure_eight_aggressive.yaml` |

```yaml
sim:
  dt_s: 0.01
  attitude: quat   # optional; default euler
```

Controllers and metrics still consume **Euler 12-state** (via bus bridges). Optional observers: [estimation.md](estimation.md).

### Next SIL (after 5c/5d — ROADMAP Now)

| ID | Change | Why |
|----|--------|-----|
| **D-7 / D-8** | Motor dynamics + mixer / allocation | Fidelity for later HIL; arm length used |
| **D-13 / V-7** | Flexible / elastic lumped states | Research airframes |
| **D-4 / D-5** | Drag / aero in \(f\) | Optional fidelity |

Gentle figure-eight / square demos remain the Euler regression baseline.

### Where it is used

```text
Controller.compute → ActuatorCommand u
       ↓
SimPlant.step / closed_loop RHS  (+ optional observer on MeasurementBus)
       ↓
DynamicsModel.f(x, u, vehicle) → xdot
  (EulerRigidBodyDynamics → state_derivative
   QuatRigidBodyDynamics  → state_derivative_quat)
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

Enablement for research (drag, motors, flex). Tracked in [EXTENSIBILITY_TODO.md](EXTENSIBILITY_TODO.md).

### Done — Dynamics backend protocol (D-3)

```text
DynamicsModel
  id / attitude / state_dim / control_dim
  f(x, u, vehicle) -> xdot
  # optional linearize later
```

Shipped: `EulerRigidBodyDynamics`, `QuatRigidBodyDynamics`; `SimPlant` injects via `sim.attitude` (or custom `dynamics=`). Study-selected named backends beyond euler/quat (S-4 full) still open.

### Next — Vehicle aero / param bag (D-4)

- Extend `VehicleParams` (or nested `aero:`) with optional fields, e.g.  
  `drag_lin_ns_m`, `drag_quad_ns2_m2`, `c_mq` (pitch damping), etc.
- Keep defaults **zero** so existing studies bit-match.
- Document units in vehicle guide.

### Next — Drag / damping models (D-5)

- Implement `f` terms: linear/quadratic translational drag in NED or body;  
  optional rotor-induced or rate damping on \(\omega\).
- Update or replace hover linearization (numerical finite-difference fallback is OK).
- Add unit tests: energy dissipation, hover trim still holds when \(v=0\).

### Next — Propeller / motor dynamics (D-7)

- First-order lag on thrust or motor RPM states → **state dimension change**.
- Requires careful state layout docs + controller awareness (or outer wrench still commanded).
- Export / metrics state maps must version.

### Next — Control allocation (D-8)

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
| `DynamicsModel` + Euler/quat plants | **Done** (D-3, D-10 core) |
| SO(3) attitude error in control/metrics | **Done** |
| Translational drag (vehicle / prop) | **TODO** — not in \(f\) |
| Aero moments / rate damping | **TODO** |
| Study-selected custom dynamics type beyond euler/quat | **Partial** (S-4) |
| Numeric linearization helper | **TODO** |
| Motor/prop states | **TODO** (D-7) |
| Mixer / allocation | **TODO** (D-8) |
| Wind / disturbance injection | **TODO** (could be \(u\) or force in \(f\)) |
| Native 13-state timeseries export | **TODO** (optional) |

Prefer a new `DynamicsModel` subclass (or optional aero terms inside the default models) over forking `closed_loop` for research plant changes.
