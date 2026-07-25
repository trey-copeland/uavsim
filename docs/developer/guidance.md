# Guidance & navigation

**Packages:** `uavsim.guidance` (planners), `uavsim.reference` (trajectory contract)  
**Missions:** `configs/missions/`  
**Study block:** `guidance:` in study YAML  

Guidance **produces** a `ReferenceTrajectory`. The sim loop and controllers only call `reference.evaluate(t)`.

---

## Concepts

| Concept | Owner | Role |
|---------|-------|------|
| Mission file / hold params | config | What to fly |
| `GuidanceBackend` | `guidance` | Algorithm: mission + vehicle → reference |
| `ReferenceTrajectory` | `reference` | Time-parameterized \(x_\mathrm{ref}(t)\) |
| `FeasibilityReport` | `reference` | Pre-sim warnings/fails on the reference |

**Registry API** (backends):

```python
from uavsim.guidance import register_guidance, create_guidance, list_guidance_backends
```

Core registrations: `hold`, `waypoints`, **`intercept_pursue`** (import side effects in `guidance/__init__.py`).

---

## Built-in: hold

Constant NED position + yaw for a duration.

```yaml
guidance:
  type: hold
  position_ned_m: [0.0, 0.0, 0.0]   # z positive down
  yaw_rad: 0.0
  duration_s: 5.0
```

Python:

```python
from uavsim.reference import hold_at_ned
import numpy as np
ref = hold_at_ned(np.array([0.0, 0.0, 0.0]), yaw_rad=0.0, duration_s=5.0)
sample = ref.evaluate(1.0)  # sample.x_ref shape (12,)
```

---

## Built-in: waypoints

### Mission file (`configs/missions/*.yaml`)

```yaml
schema_version: 1
name: gentle_square
frame: NED
waypoints:
  - {label: start, time: 0.0, x: 0.0, y: 0.0, z: 1.0, yaw: 0.0}
  - {label: right, time: 5.0, x: 2.0, y: 0.0, z: 1.0, yaw: 0.0}
  # ...
```

- Times must be **strictly increasing**.
- `yaw: null` allowed when yaw policy can fill (e.g. path tangent).
- Optional velocity/accel fields for min-snap BCs (see mission schema).

JSON / heritage `.wpt` load is also supported by `load_mission`.

### Study YAML

```yaml
guidance:
  type: waypoints
  mission_file: configs/missions/gentle_square.yaml
  method: auto          # auto | interp | minsnap
  yaw_mode: constant    # constant | path_tangent | from_waypoints
  sample_dt_s: 0.01
  fail_on_infeasible: false
```

| `method` | Behavior |
|----------|----------|
| `interp` | Akima / MAKIMA-class smooth position + numeric derivatives |
| `minsnap` | Per-axis 7th-order min-snap QP (Mellinger-style) |
| `auto` | Heritage policy: if **any** segment \(< 3\) s → interp; else minsnap |

| `yaw_mode` | Behavior |
|------------|----------|
| `constant` | Fixed yaw (default demo) |
| `path_tangent` | Heading from horizontal velocity (can be infeasible on tight curves) |
| `from_waypoints` | Interpolate explicit waypoint yaw; NaNs filled carefully |

### Feasibility

After plan, `FeasibilityReport` checks peak attitude demand, speed, yaw rate/accel, etc. Stored in run dir as `guidance/feasibility.json`. Policy: **warn by default**; `fail_on_infeasible: true` raises.

Domain lesson: **path-tangent auto-yaw on figure-eights** often fails — prefer `yaw_mode: constant` for demos.

---

## How to add a guidance backend

### Architecture checklist

1. **Mission schema** — Pydantic model with `type: Literal["my_backend"]` under `GuidanceConfig` union in `studies/config.py`.
2. **Backend class** — implement `id`, `plan`, and default `update → None`.
3. **`register_guidance("my_backend", MyBackend)`** at import time.
4. **Emit** only `uavsim.reference.ReferenceTrajectory` (e.g. `SampledReference` or `HoldReference`).
5. **Pipeline wiring** — today `_build_guidance` in `studies/pipeline.py` is a manual switch (**TODO:** drive purely from registry + config).
6. **`guidance_mission_dict`** — map study config → `plan(mission, vehicle)` dict.
7. **Tests** — unit plan smoke + optional closed-loop integration; registry stub pattern in `tests/unit/test_guidance_registry.py`.

### Minimal backend

```python
# src/uavsim/guidance/my_backend.py
from uavsim.guidance.base import PlanResult, register_guidance
from uavsim.reference import check_reference_feasibility, hold_at_ned
import numpy as np

class CircleHoldGuidance:
    id = "circle_hold"  # example offline product

    def plan(self, mission, vehicle, *, rng=None):
        # mission may contain radius, duration, ...
        pos = np.array(mission.get("center_ned_m", [0.0, 0.0, 1.0]))
        ref = hold_at_ned(pos, duration_s=float(mission.get("duration_s", 5.0)))
        ref.backend_id = self.id
        feas = check_reference_feasibility(ref, vehicle)
        return PlanResult(reference=ref, feasibility=feas, diagnostics={})

    def update(self, *args, **kwargs):
        return None  # offline

register_guidance("circle_hold", CircleHoldGuidance)
```

Import the module from `guidance/__init__.py` so registration runs.

For a **true** geometric path, prefer a `SampledReference` dense grid (see `reference/types.py`) rather than abusing hold.

### Online / replan (G-6) — **shipped**

`GuidanceBackend.update(...)` is called from **fixed-step** closed-loop when a `GuidanceLoop` is attached (study `guidance.type: intercept_pursue`).

| Piece | Status |
|-------|--------|
| Protocol method | **Done** |
| Called from closed-loop | **Done** — `sim.closed_loop.GuidanceLoop` + `InProcessControllerAdapter.set_reference` |
| `intercept_pursue` | **Done** — seed climb mission + scripted target; CV lead-point short-horizon replan after `replan_start_s` |
| Capture metrics | `metrics.capture_target_mission` + `intercept_success` / `min_range_m` (not tracking RMSE) |
| RNG / MC interaction for replan | **Partial** — replan uses plant state / \(\hat x\); no extra replan RNG |

**Study examples**

```yaml
guidance:
  type: intercept_pursue
  seed_mission_file: configs/missions/tutorials/intercept_seed_climb.yaml
  target_mission_file: configs/missions/tutorials/intercept_l0_target.yaml
  replan_period_s: 0.2
  replan_start_s: 2.5      # stay on seed through pad/GE climb
  lead_time_s: 1.2
  capture_radius_m: 1.0
  horizon_s: 3.0
  duration_s: 10.0
  state_source: estimate   # truth | estimate
```

Demos: `configs/studies/tutorials/intercept_online_*.yaml` · live pack: `docs/demos/intercept/`.

---

## TODOs / gaps (guidance & nav)

| Gap | Status |
|-----|--------|
| Pipeline uses **hard-coded** hold/waypoints/**intercept** switch instead of pure registry | **Partial** — third backends still edit pipeline |
| Non-waypoint family (helix, corridor, landing profile) | **TODO** / Phase 6 |
| In-loop `update` / replan | **Done** (G-6 + intercept_pursue) |
| Mixed multi-segment missions (takeoff → transit → hover) | **Partial** — seed + online intercept is a teaching pattern |
| External trajectory ingest | **TODO** |
| Polyglot min-snap QP swap | **Open** (interface boundary exists; solver is NumPy KKT) |

See [EXTENSIBILITY_TODO.md](EXTENSIBILITY_TODO.md) and SPEC deferred nav list.
