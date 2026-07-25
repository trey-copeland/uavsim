---
tutorial_id: T-GUIDE-ONLINE
title: Online intercept guidance (G-6)
---

# Online intercept — how this stack is built

**Goal:** Run a pad-climb intercept with **online reference replan**, understand the pieces you would touch to extend it, and interpret **capture** vs tracking metrics.

**Prerequisites:** `uv sync --extra dev` from the repo root; Python 3.11+.

**Related:** [guidance.md](../developer/guidance.md) · [demo SPA](../demos/intercept/) · study ladder in [`configs/studies/tutorials/README.md`](../../configs/studies/tutorials/README.md)

---

## 1. What you get

| Layer | Role in this demo |
|-------|-------------------|
| **Vehicle** | Sized quadrotor + Cheeseman **ground effect** at pad + optional **battery** |
| **Seed mission** | Pad → climb only (`intercept_seed_climb.yaml`) |
| **Target** | Open-loop scripted path (`intercept_l0_target.yaml`) — **not** a second plant |
| **Guidance** | `intercept_pursue`: seed until `replan_start_s`, then **lead-point replan** |
| **Control** | Cascade **NDI** on \(\hat x\) / truth |
| **Estimation** | **MEKF** + channels `pos`, `omega` (GPS + gyro teaching stack) |
| **Success** | \(\min_t \|p_{\mathrm{own}}-p_{\mathrm{tgt}}\| \le 1\,\mathrm{m}\) → `intercept_success` |

Open-loop L0 studies still exist for a simpler ladder step; the **hero** recipe is online.

---

## 2. Run the hero study

```bash
# from repo root
uv run uavsim simulate configs/studies/tutorials/intercept_online_success.yaml
```

Inspect the run directory printed by the CLI:

```bash
# replace with your timestamped path
RUN=runs/intercept_online_success_<timestamp>
cat $RUN/nominal/metrics.json | head   # or use jq
```

**Fields that matter for this tutorial**

| Key | Meaning |
|-----|---------|
| `intercept_success` | Capture within `capture_radius_m` of the **scripted target** |
| `min_range_m` | Closest approach to target |
| `n_replans` | How many times online guidance rewrote \(x_r\) |
| `observer_id` | e.g. `mekf` |
| `soc_final` / `energy_depleted` | Battery bookkeeping (if vehicle has `battery.enabled`) |
| `success` (tracking) | Peak error vs **reference** + attitude bounds — **often false** under online replan |

Do **not** treat tracking `success` as intercept success. Online \(x_r\) moves every replan; RMSE can look terrible while min-range is &lt; 1 m.

---

## 3. Config map (study YAML)

Hero file: [`configs/studies/tutorials/intercept_online_success.yaml`](../../configs/studies/tutorials/intercept_online_success.yaml)

```yaml
vehicle: configs/vehicles/tutorials/intercept_quadrotor.yaml

controller:
  type: ndi_cascade
  # gains …

guidance:
  type: intercept_pursue
  seed_mission_file: configs/missions/tutorials/intercept_seed_climb.yaml
  target_mission_file: configs/missions/tutorials/intercept_l0_target.yaml
  replan_period_s: 0.2
  replan_start_s: 2.5      # stay on seed through pad / GE climb
  lead_time_s: 1.2          # CV lead: p* = p_t + v_t * lead
  capture_radius_m: 1.0
  horizon_s: 3.0            # short-horizon ownship segment length
  duration_s: 10.0
  state_source: estimate    # truth | estimate — replan from x̂ vs plant
  seed_method: minsnap

sim:
  attitude: quat
  plant: wrench
  observer:
    type: mekf
    channels: [pos, omega]

metrics:
  capture_target_mission: configs/missions/tutorials/intercept_l0_target.yaml
  capture_radius_m: 1.0

initial_state:
  position_ned_m: [0.0, 0.0, 3.05]   # pad (NED z+ down; GE vehicle ground_z ≈ 3.10)
```

### Knobs you will actually turn

| Knob | Effect |
|------|--------|
| `replan_start_s` | Too early → replan while still in GE / pad; too late → miss intercept geometry |
| `lead_time_s` | Larger lead → earlier cut-in; too large → overshoot / saturation |
| `horizon_s` | Short segment length each replan (NDI needs smooth `a_ref` on the segment) |
| `state_source` | `estimate` is the honest sense-driven story; `truth` for debugging G-6 alone |
| `capture_radius_m` | Definition of “close enough” |

---

## 4. Architecture: what code path runs

```text
prepare_study
  └─ InterceptPursueGuidance.plan(seed + target)
       seed → initial ReferenceTrajectory
       target → stored open-loop path (evaluate only)

simulate_closed_loop (fixed-step when guidance_loop / quat / observer)
  each replan_period after replan_start:
    GuidanceLoop → backend.update(x or x̂, t, …)
         → new SampledReference (lead point)
         → InProcessControllerAdapter.set_reference(...)
    controller.compute(t, measurements, reference.evaluate(t))
    plant step; MEKF predict/update
```

| Package | Responsibility |
|---------|----------------|
| `uavsim/guidance/intercept/` | Lead-point math + backend |
| `uavsim/sim/closed_loop.py` | `GuidanceLoop`, replan hook |
| `uavsim/sim/adapters.py` | `set_reference` rebind |
| `uavsim/studies/pipeline.py` | Study config → guidance + loop |
| `uavsim/studies/config.py` | `InterceptPursueGuidanceConfig` |

**Import rules:** `control` still does not import `guidance`. Controllers only see `ReferenceSample`.

---

## 5. How `intercept_pursue` thinks

1. **Seed phase** (`t < replan_start_s`): fly the climb waypoints (GE active near pad).  
2. **Target** at time \(t\): evaluate scripted mission → \(p_t, v_t\).  
3. **Lead point:** \(p^\star = p_t + v_t\, t_{\mathrm{lead}}\) (constant-velocity).  
4. **Replan:** short linear segment from **current** ownship position to \(p^\star\) (dense `SampledReference` with velocity + yaw facing the intercept).  
5. **Capture:** when \(\|p-p_t\| \le r_{\mathrm{capture}}\), switch to tracking the target position for the rest of the mission.

This is **not** pure pursuit with radar noise, not multi-vehicle dynamics, and not PN. It is a teaching implementation of **online \(x_r\)** with a known target trajectory.

---

## 6. Ladder: open-loop vs online

| Study | Guidance | Observer | Use when |
|-------|----------|----------|----------|
| `intercept_l0_success.yaml` | waypoints open-loop | none | Prove plant + NDI + geometry |
| `intercept_l0_fail.yaml` | same, underpowered vehicle | none | Authority miss |
| **`intercept_online_success.yaml`** | **intercept_pursue** | **MEKF** | Full G-6 + sense story |
| `intercept_online_energy_fail.yaml` | online | MEKF | Battery empty (see [T-ENERGY](02_battery_energy.md)) |
| `intercept_online_success_mc.yaml` | online | MEKF | Plant MC → **P(capture)** |

```bash
# Open-loop baseline (easier capture under MC)
uv run uavsim simulate configs/studies/tutorials/intercept_l0_success.yaml

# Online + MEKF
uv run uavsim simulate configs/studies/tutorials/intercept_online_success.yaml

# Plant MC on online stack (slow)
uv run uavsim study configs/studies/tutorials/intercept_online_success_mc.yaml --shards 8
```

On the online MC recipe used for the demo pack, plant scatter + estimate replan yields **P(capture) ≈ 0.28** (not 1.0). Open-loop L0 MC on the same airframe was ≈ **1.0**. That gap is intentional teaching: **online + noise + plant uncertainty is harder**.

---

## 7. Interactive demo

```bash
cd docs/demos/intercept
python -m http.server 8765
# http://127.0.0.1:8765/
```

Rebuild the data pack after new MC runs (see [demo README](../demos/intercept/README.md)):

```bash
uv run python docs/demos/intercept/scripts/export_demo_data.py \
  --success-run runs/intercept_online_success_mc_<ts> \
  --fail-run runs/intercept_online_energy_fail_<ts> \
  --with-bands --band-max-trials 80
```

UI shows 3D path, attitude (with thrust vectors via shared `UavFlightViz`), 2D path + **seaborn-style MC CI tube**, range, battery, histogram of `min_range_m`.

---

## 8. “How would I extend this?”

Checklist for a **new online guidance backend** (same seams as intercept):

1. Implement `id`, `plan`, `update` → `PlanResult` with `ReferenceTrajectory` only.  
2. `register_guidance("my_id", MyClass)` and import from `guidance/__init__.py`.  
3. Add a pydantic config under `GuidanceConfig` union in `studies/config.py`.  
4. Branch in `_build_guidance` / `guidance_mission_dict` (registry-only pipeline is still a backlog item).  
5. Force fixed-step path when `GuidanceLoop` is active (already done for online).  
6. Unit-test pure helpers without the plant; integration study smoke with short `duration_s`.

Anti-patterns: putting motor counts in the controller; importing guidance from `control`; treating tracking RMSE as capture.

---

## 9. Honesty (read before presenting)

| Claim | Reality |
|-------|---------|
| Second vehicle | Target is a **mission file**, not a closed-loop plant |
| Perfect sense | MEKF + channel noise; simplified error dynamics (see [LIMITATIONS](../LIMITATIONS.md)) |
| Battery kills thrust | **No** — empty SOC is logged; plant still flies (v1) |
| P(capture) on demo | From **plant MC** on the online recipe; rebuild pack after changing geometry |

---

## 10. Next reads

- [T-ENERGY — battery model](02_battery_energy.md)  
- [developer/guidance.md](../developer/guidance.md) — protocol + online status  
- [LIMITATIONS.md](../LIMITATIONS.md) — scope  
- Plan: [ONLINE_INTERCEPT_AND_BATTERY.md](../../plan/ONLINE_INTERCEPT_AND_BATTERY.md)
