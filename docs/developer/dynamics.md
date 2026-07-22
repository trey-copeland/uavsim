# Dynamics: model today and how to extend it

**Package:** `uavsim.dynamics`  
**Core EOM:** `dynamics/nonlinear.py` → `state_derivative` / `state_derivative_quat`  
**Linearization:** `dynamics/linearize.py` → `hover_linearization(vehicle)` for LQR  
**Protocol:** `dynamics/model.py` → `DynamicsModel` (`EulerRigidBodyDynamics`, `QuatRigidBodyDynamics`)  
**Plant:** `sim/plant.py` → `SimPlant` injects a `DynamicsModel` each step  

---

## Model today (what is implemented)

Rigid-body 6DOF quadrotor, **body wrench control** (default). Attitude: **ZYX Euler** plant by default, or **unit-quaternion** plant via study config. Optional **motors** plant (first-order ω). Optional **aero** (drag / prop H / ground effect) via `vehicle.aero` — **off by default**.

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

### Motors + mixer (D-7 / D-8 — landed)

Control laws still command **body wrench** \(u\). Optional plant path:

1. **Mixer (allocation):** \(u \leftrightarrow f_{1:4}\) via X-quad geometry + `arm_length_m` + `ct`/`cq`  
2. **Motors:** first-order lag on speeds \(\omega_i\); \(f_i = c_T \omega_i^2\); realized wrench from mixer  

```yaml
sim:
  plant: motors   # default: wrench (instantaneous body force/torque)
  attitude: euler # or quat (+ 4 motor states)
```

Vehicle `propulsion:` block (see `configs/vehicles/default_quadrotor.yaml`).  
Demo: `configs/studies/figure_eight_motors.yaml`.

| ID | Status |
|----|--------|
| **D-8** mixer / allocation | **Done** — `dynamics/mixer.py` |
| **D-7** first-order motor states | **Done** — `dynamics/motors.py` (`euler_motors` / `quat_motors`) |
| **D-4 / D-5** drag / aero / GE | **Done** — `dynamics/aero.py`; `AeroParams` (defaults off) |
| **D-13 / V-7** flexible body | **TODO** |

Gentle figure-eight / square demos remain the Euler **wrench** regression baseline (aero off).

### Aero / environment (D-4 / D-5 + ground effect)

Applied inside `state_derivative` / `state_derivative_quat` (so motors plant inherits them):

| Effect | Model | Params |
|--------|--------|--------|
| Body drag | \(F_d = -b_\ell v - b_q \|v\| v\) (NED) | `drag_lin_ns_m`, `drag_quad_ns2_m2` |
| Rate damping | \(\tau_d = -c\,\omega\) | `rate_damp_nm_s` |
| Prop H-force | \(f_{xy}^\text{body} = -k_h\,T\,v_{xy}\) | `prop_h_s_per_m` |
| Ground effect | Thrust \(\times\kappa(h)\); Cheeseman–Bennett or exp | `ground_effect`, `rotor_radius_m`, `ground_z_ned_m`, … |

Height AGL (NED \(z+\) down): \(h = z_\text{ground} - z\).  
Demos: `configs/vehicles/default_quadrotor_aero.yaml` + `figure_eight_aero.yaml`;  
`default_quadrotor_ge.yaml` + `hover_ground_effect.yaml`.

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

### Done — Vehicle aero / drag / GE (D-4 / D-5)

- `AeroParams` nested on vehicle; defaults off.
- Body lin/quad drag, rate damping, lumped prop H-force, ground-effect κ on thrust.
- Hover linearization includes **linear** drag and rate damp only.

### Done — Propeller / motor dynamics (D-7) + mixer (D-8)

- First-order motor ω states + X-quad allocation (`sim.plant: motors`).

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
| Body drag + prop H-force + rate damp | **Done** (D-4/D-5; `aero.py`, defaults off) |
| Ground-effect κ on thrust | **Done** (Cheeseman / exp; `AeroParams.ground_effect`) |
| Motor/prop first-order states | **Done** (D-7; `sim.plant: motors`) |
| Mixer / allocation | **Done** (D-8; X-quad) |
| Study-selected custom dynamics type beyond euler/quat/motors | **Partial** (S-4) |
| Numeric linearization helper | **TODO** (D-6) |
| Wind / disturbance injection | **TODO** (D-9) |
| Flexible / elastic modes | **TODO** (D-13 / V-7) ← next plant fidelity |
| Native 13-state timeseries export | **TODO** (optional polish) |

Prefer a new `DynamicsModel` subclass (or optional aero terms inside the default models) over forking `closed_loop` for research plant changes.
