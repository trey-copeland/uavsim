# Defining a vehicle

**Package:** `uavsim.vehicles`  
**Code:** `src/uavsim/vehicles/params.py`  
**Configs:** `configs/vehicles/`

A **vehicle** is physical parameters + actuator limits. It does **not** own equations of motion (that is `dynamics`). Controllers, guidance feasibility, and the plant all consume the same `VehicleParams` object.

---

## What you can configure today

YAML fields map 1:1 to the Pydantic model `VehicleParams`:

| Field | Meaning | Units |
|-------|---------|--------|
| `schema_version` | Config schema id (currently `1`) | — |
| `vehicle_id` | Short name for manifests / exports | string |
| `mass_kg` | Mass | kg |
| `gravity_m_s2` | Gravity magnitude (NED down-positive dynamics use \(+mg\) on \(z\)) | m/s² |
| `arm_length_m` | Arm length (mixer D-8) | m |
| `inertia.ixx_kg_m2` … `izz_kg_m2` | Principal inertia (diagonal only) | kg·m² |
| `limits.thrust_min_n` / `thrust_max_n` | Total thrust bounds | N |
| `limits.torque_max_nm` | Symmetric body torque limit on each axis | N·m |
| `propulsion.*` | Mixer / motors (`ct`, `cq`, τ_m, ω limits) | see default YAML |
| `aero.*` | Optional drag / prop H / ground effect (**off** by default) | see [dynamics.md](dynamics.md) |

Helpers on the loaded model:

- `hover_thrust_n()` → \(m g\)
- `u_hover()` → \([mg, 0, 0, 0]\)
- `limits.u_min()` / `u_max()` → length-4 arrays for saturation

### Example: new vehicle file

Create `configs/vehicles/my_quad.yaml`:

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
  thrust_max_n: 30.0      # should cover hover + maneuver margin
  torque_max_nm: 2.0
```

Point a study at it:

```yaml
# configs/studies/my_hover.yaml
vehicle: configs/vehicles/my_quad.yaml
controller:
  type: lqr_hover
  Q_diag: [100, 100, 100, 10, 10, 1, 10, 10, 10, 1, 1, 0.1]
  R_diag: [0.1, 1.0, 1.0, 1.0]
guidance:
  type: hold
  position_ned_m: [0.0, 0.0, 0.0]
  duration_s: 5.0
```

```bash
uv run uavsim simulate configs/studies/my_hover.yaml
```

### Load in Python

```python
from uavsim.vehicles.params import load_vehicle, default_vehicle

v = load_vehicle("configs/vehicles/default_quadrotor.yaml")
# or in-memory defaults:
v = default_vehicle()
print(v.mass_kg, v.u_hover())
```

---

## Design rules

1. **Keep mass properties out of controller code** — pass `VehicleParams` into design/factory.
2. **Thrust max should exceed hover** (\(F_\max > mg\)) or altitude recovery is impossible.
3. **Torque limits** interact strongly with LQR \(R\) and initial offsets; too tight → permanent saturation.
4. **MC perturbations** (mass, inertia, arm) are defined in study `monte_carlo:` and applied via `uavsim.monte_carlo.perturb` — they clone/modify `VehicleParams`, not a parallel schema.

---

## Testing a vehicle change

- Unit: load YAML, check `hover_thrust_n ≈ m g`, `u_min/u_max` shape.
- Integration: short hover or `hover_from_offset` with your vehicle path.
- After dynamics extensions (drag): keep the same vehicle file as the single source of \(m,I\).

---

## TODOs / gaps (vehicles)

| Gap | Why it matters | Status |
|-----|----------------|--------|
| Off-diagonal inertia products | Real CAD inertia tensors | **TODO** — model is diagonal-only |
| Battery / extra mission params | Endurance studies | **TODO** — `extra="forbid"` until schema extended |
| Propulsion `ct` / `cq` / motor τ / ω limits | Mixer + motor plant | **Done** — optional `propulsion:` block |
| Aero drag / prop H / ground effect | Nonlinear \(f\) | **Done** — `aero:` defaults off; demos `*_aero.yaml`, `*_ge.yaml` |
| Control allocation / mixer | Map wrench ↔ motor forces; arm length used | **Done** — `sim.plant: motors` |
| Multi-vehicle / heterogeneous fleets | Formation, different platforms | **Out of core scope** |
| Validation \(F_\max \ge mg\) as hard error | Catch bad configs early | **TODO** (soft today) |

See also [EXTENSIBILITY_TODO.md](EXTENSIBILITY_TODO.md).
