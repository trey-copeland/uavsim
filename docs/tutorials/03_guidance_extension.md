---
tutorial_id: T-GUIDE-PLUGIN
title: Extend guidance — registry, plan, and online replan
---

# Extend guidance — how intercept plugged into `uavsim`

**Goal:** Understand the **guidance extension seam** by walking the same path `intercept_pursue` took: registry → `plan` / `update` → study config → pipeline → closed-loop rebind. Use this when adding a new offline planner or another online replan mode.

**Prerequisites:** [T0](00_first_run.md); skim [01_online_intercept.md](01_online_intercept.md).  
**Contracts:** [guidance.md](../developer/guidance.md) · [ARCHITECTURE.md](../ARCHITECTURE.md)

---

## 1. Mental model

```text
Study YAML  guidance:
  type: <backend_id>
        │
        ▼
  registry  create_guidance(id, **kwargs)
        │
        ▼
  backend.plan(mission, vehicle)  →  ReferenceTrajectory  (offline seed / full path)
        │
        ▼  (optional G-6)
  fixed-step sim ──► backend.update(state, t, …)
        │                 │
        │                 └── set_reference(new_ref) on controller adapter
        ▼
  metrics vs commanded x_r samples  (+ optional capture vs scripted target)
```

| Layer | Owns |
|-------|------|
| **`guidance`** | Algorithm: mission + vehicle → reference; optional in-loop replan |
| **`reference`** | Backend-agnostic \(x_r(t)\) (`HoldReference`, `SampledReference`, …) |
| **`control`** | `compute(t, measurements, ref)` only — **must not** import guidance |
| **`sim`** | `GuidanceLoop` + `InProcessControllerAdapter.set_reference` |

Hard rule from the developer hub: **control does not import guidance**. Controllers only see `ReferenceSample` objects.

---

## 2. Registry (G-5 style)

Built-in backends register at import time:

```python
from uavsim.guidance import list_guidance_backends, create_guidance

list_guidance_backends()
# → ['hold', 'intercept_pursue', 'waypoints', …]

backend = create_guidance("hold")  # or kwargs for constructors that take them
```

| Backend id | Offline `plan` | Online `update` |
|------------|----------------|-----------------|
| `hold` | Constant NED + yaw | no |
| `waypoints` | Mission file → dense path | no |
| `intercept_pursue` | Seed climb path + load scripted target | **yes** — CV lead-point segments |

**Registration pattern** (see `src/uavsim/guidance/hold.py`, `waypoints/backend.py`, `intercept/backend.py`):

```python
from uavsim.guidance.base import PlanResult, register_guidance

class MyGuidance:
    id = "my_backend"

    def plan(self, mission, vehicle, *, rng=None):
        ...
        return PlanResult(reference=ref, feasibility=feas, diagnostics={})

    def update(self, state, t, mission, vehicle, reference, *, rng=None):
        return None  # offline-only

register_guidance("my_backend", MyGuidance)
```

Import the module from `uavsim/guidance/__init__.py` so registration runs when the package loads (side-effect imports — same pattern as hold/waypoints/intercept).

```bash
# smoke
uv run python -c "from uavsim.guidance import list_guidance_backends; print(list_guidance_backends())"
```

---

## 3. Protocol: `plan` vs `update`

Defined in `uavsim.guidance.base.GuidanceBackend`:

| Method | When | Return |
|--------|------|--------|
| **`plan(mission, vehicle)`** | Study prepare / nominal start | `PlanResult` with `reference` + `FeasibilityReport` |
| **`update(state, t, mission, vehicle, reference)`** | Fixed-step loop when `GuidanceLoop` is attached | `PlanResult` to rebind, or **`None`** to keep current ref |

**Offline-only** backends (hold, waypoints): `update` always returns `None`.

**Online** (`intercept_pursue`):

1. `plan` — waypoints seed (pad climb) + load **scripted** target trajectory (not a second plant).  
2. `update` — after `replan_start_s`, on a period `replan_period_s`, predict lead point \(p^* = p_t + v_t \cdot t_{\mathrm{lead}}\), emit a short-horizon `SampledReference`, rebind the adapter.

Closed-loop wiring lives in `sim/closed_loop.py` (`GuidanceLoop`, `_maybe_replan`) and is enabled from the study pipeline when `guidance.type: intercept_pursue`.

---

## 4. Study config + pipeline (today’s reality)

### Config union

New backends need a Pydantic block under `GuidanceConfig` in `src/uavsim/studies/config.py` (see `InterceptPursueGuidanceConfig`). Field names map into constructor kwargs and `guidance_mission_dict`.

Example study fragment:

```yaml
guidance:
  type: intercept_pursue
  seed_mission_file: configs/missions/tutorials/intercept_seed_climb.yaml
  target_mission_file: configs/missions/tutorials/intercept_l0_target.yaml
  replan_period_s: 0.2
  replan_start_s: 2.5
  lead_time_s: 1.2
  horizon_s: 3.0
  duration_s: 10.0
  state_source: estimate   # truth | estimate
```

### Manual switch (honest gap)

`_build_guidance` in `studies/pipeline.py` is still a **hand-written** `if isinstance(...):` for hold / waypoints / intercept. Registry alone is not enough for CLI studies until that switch (or a pure factory path) is extended.

**Checklist when adding a backend:**

1. Pydantic guidance config + union member  
2. Backend class + `register_guidance` + import in `guidance/__init__.py`  
3. Branch in `_build_guidance` + mission dict mapping  
4. Emit only `ReferenceTrajectory` types from `uavsim.reference`  
5. Unit test: registration + `plan` smoke (`tests/unit/test_g6_replan.py` / registry tests)  
6. Optional integration: closed-loop if `update` is non-trivial  

---

## 5. Walk the intercept code (map)

| Concern | Location |
|---------|----------|
| Backend + register | `src/uavsim/guidance/intercept/backend.py` |
| CV lead predict | `src/uavsim/guidance/intercept/predict.py` |
| Package export / import | `src/uavsim/guidance/__init__.py` |
| Study config model | `InterceptPursueGuidanceConfig` in `studies/config.py` |
| Pipeline build + `GuidanceLoop` | `studies/pipeline.py` → `run_closed_loop_trial` |
| Replan tick | `sim/closed_loop.py` (`_maybe_replan`) |
| Adapter rebind | `sim/adapters.py` (`set_reference`) |
| Capture metrics | `metrics` + `capture_target_mission` on study |
| Tracking metrics | Per-tick `ClosedLoopResult.x_ref` — see [LIMITATIONS](../LIMITATIONS.md) |

Run the hero recipe after reading:

```bash
uv run uavsim simulate configs/studies/tutorials/intercept_online_success.yaml
# inspect n_replans, intercept_success, tracking_vs_commanded_reference
```

---

## 6. What *not* to put in a guidance backend

| Temptation | Prefer |
|------------|--------|
| Motor counts / mixer math | Vehicle + plant |
| LQR/NDI gains | `control` |
| Sensor noise models | `estimation` / observer config |
| Capture KPI definition | Study `metrics:` + post metrics (target mission path) |
| Second full 6-DoF chase vehicle | Out of scope — target is **scripted** reference |

---

## 7. Related tutorials

| Guide | Role |
|-------|------|
| [00_first_run.md](00_first_run.md) | Install / simulate / report |
| [01_online_intercept.md](01_online_intercept.md) | User-facing intercept config + capture vs tracking |
| [02_battery_energy.md](02_battery_energy.md) | Opt-in energy (orthogonal to guidance) |
| [04_vehicle_yaml.md](04_vehicle_yaml.md) | Clone a vehicle YAML for mass / limits |
| [guidance.md](../developer/guidance.md) | Full API and feasibility notes |

---

## Anti-patterns

- Importing `guidance` from `control`  
- Re-evaluating only the final `adapter.reference` after online replan for RMSE  
- Treating registry registration as “study ready” without pipeline + config wiring  
- Building a second plant for the intercept target when a scripted mission is enough  
