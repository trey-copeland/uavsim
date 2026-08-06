---
tutorial_id: T-VEH-YAML
title: Point a study at a new quadrotor YAML
---

# Vehicle YAML — clone, retune, point a study

**Goal:** Create a **new X-quadrotor vehicle file**, point a study at it, and re-run. No multi-layout / tilt-rotor work — same stock airframe family as the rest of the portfolio.

**Prerequisites:** [T0](00_first_run.md).  
**Contracts:** [vehicles.md](../developer/vehicles.md) · [LIMITATIONS.md](../LIMITATIONS.md)

---

## 1. What a vehicle owns

A vehicle YAML is **physical parameters + limits** (and optional aero / battery). It does **not** own:

- Equations of motion (`dynamics`)  
- Gains (`control`)  
- Missions (`guidance` / mission files)

| Field group | Examples |
|-------------|---------|
| Mass / inertia / arm | `mass_kg`, `inertia.*`, `arm_length_m` |
| Limits | `thrust_max_n`, `torque_max_nm` |
| Propulsion (mixer) | `propulsion.ct_n_s2`, motor τ, ω limits |
| Aero (opt-in) | drag, **ground effect**, … — off unless set |
| Battery (opt-in) | SOC bookkeeping — see [02_battery_energy.md](02_battery_energy.md) |

Helpers after load: `hover_thrust_n()` → \(mg\), `u_hover()` → \([mg,0,0,0]\).

---

## 2. Clone a template

**Minimal / default path** (portfolio studies):

```text
configs/vehicles/default_quadrotor.yaml
```

**Intercept-class demo vehicle** (heavier, high T/W, pad GE + battery):

```text
configs/vehicles/tutorials/intercept_quadrotor.yaml
```

Copy either to a new id (do not overwrite shared portfolio vehicles until you mean to):

```bash
# from repo root
cp configs/vehicles/default_quadrotor.yaml configs/vehicles/my_quad.yaml
# edit vehicle_id, mass_kg, limits, …
```

Minimum useful body:

```yaml
schema_version: 1
vehicle_id: my_quad

mass_kg: 1.2
gravity_m_s2: 9.81
arm_length_m: 0.28

inertia:
  ixx_kg_m2: 0.015
  iyy_kg_m2: 0.015
  izz_kg_m2: 0.028

limits:
  thrust_min_n: 0.0
  thrust_max_n: 30.0      # must cover hover + maneuver margin
  torque_max_nm: 2.0
```

**Rule of thumb:** \(F_{\max} \gtrsim 2\,mg\) for gentle hover demos; intercept demos use higher T/W (`intercept_quadrotor` is ~4.5).

---

## 3. Point a study at it

Create a small study (or copy `configs/studies/hover_from_offset.yaml`):

```yaml
# configs/studies/my_hover.yaml
schema_version: 1
study_id: my_hover
seed: 0

vehicle: configs/vehicles/my_quad.yaml

controller:
  type: lqr_hover
  Q_diag: [100, 100, 100, 10, 10, 1, 10, 10, 10, 1, 1, 0.1]
  R_diag: [0.1, 1.0, 1.0, 1.0]

guidance:
  type: hold
  position_ned_m: [0.0, 0.0, 0.0]
  yaw_rad: 0.0
  duration_s: 5.0

sim:
  dt_s: 0.01
  method: rk45

metrics:
  position_bound_m: 0.1

initial_state:
  position_ned_m: [0.2, -0.1, 0.1]
  euler_rad: [0.0, 0.0, 0.0]
  velocity_ned_m_s: [0.0, 0.0, 0.0]
  omega_body_rad_s: [0.0, 0.0, 0.0]
```

```bash
uv run uavsim simulate configs/studies/my_hover.yaml
uv run uavsim report runs/my_hover_<timestamp>/
```

LQR is redesigned from the **vehicle** linearization for that study — change mass and gains still use the same `Q`/`R` diagonals unless you retune them.

---

## 4. Patterns from the intercept fleet

| File | Intent |
|------|--------|
| `configs/vehicles/tutorials/intercept_quadrotor.yaml` | Hero: mass 1.5 kg, high \(F_{\max}\), Cheeseman GE at pad, battery on |
| `…/intercept_quadrotor_low_battery.yaml` | Same airframe, tiny `capacity_wh` → energy-fail narrative |
| `…/intercept_quadrotor_underpowered.yaml` | Authority stress (lower thrust ceiling) |

Study YAMLs only change `vehicle:` (and sometimes metrics); guidance/control stay the same recipe. That is the preferred teaching pattern: **swap physics, keep the mission story**.

NED reminder for pad GE: \(z\) positive **down**; AGL ≈ `ground_z_ned_m - z`. Pad ICs sit slightly below the ground plane so GE is active at takeoff.

---

## 5. Load in Python

```python
from uavsim.vehicles.params import load_vehicle

v = load_vehicle("configs/vehicles/my_quad.yaml")
print(v.vehicle_id, v.mass_kg, v.hover_thrust_n())
```

---

## 6. Related

| Doc | Role |
|-----|------|
| [vehicles.md](../developer/vehicles.md) | Full field list, propulsion, aero, battery schema |
| [02_battery_energy.md](02_battery_energy.md) | Opt-in energy integrator |
| [01_online_intercept.md](01_online_intercept.md) | Uses intercept vehicle + GE climb |
| [dynamics.md](../developer/dynamics.md) | How aero/GE enter the plant |

---

## Anti-patterns

- Editing `default_quadrotor.yaml` for a one-off experiment (breaks portfolio comparisons)  
- Setting `thrust_max_n < mg` and expecting climb  
- Putting controller gains in the vehicle file  
- Expecting multi-rotor layouts / tilt maps — backlog only ([airframes.md](../developer/airframes.md))  
