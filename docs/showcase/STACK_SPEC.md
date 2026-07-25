# Showcase closed-loop stack (provenance) specification

| Field | Value |
|-------|--------|
| **Status** | Implementation contract (Phase 0–1) |
| **Branch** | `feature/showcase-stack-provenance` |
| **UI home** | Tab id `stack` · label **System** |
| **Data field** | `runs[i].stack` on `showcase.json` |
| **Builder** | `uavsim.viz.stack.build_stack_from_run_dir` (+ gallery wiring) |

Goal: for every gallery run, the SPA can show a **closed-loop block diagram** and expand each block to reveal how that run’s data was generated — without a server or live sim (static GitHub Pages).

Out of scope for Phase 0–1: plant-fidelity mission, \(A,B\) linearization dump, per-rotor thrust UI.

---

## 1. Topology (fixed teaching graph)

Nodes (left → right conceptual flow):

| id | kind | Meaning |
|----|------|---------|
| `mission` | mission | Waypoints / timing / yaw intent |
| `guidance` | guidance | Reference generator |
| `sensors` | sensors | Measurement channels (+ noise params) |
| `observer` | observer | State estimate path |
| `controller` | controller | Law (LQR / PID / …) |
| `actuators` | actuators | Wrench command vs mixer+motors |
| `plant` | plant | Rigid-body (+ aero flags) |
| `metrics` | metrics | Bounds / scoring |

Default edges (list of `[from, to]`):

```text
mission → guidance
guidance → controller          # reference x_r
sensors → observer
observer → controller          # x̂ (or true x when identity)
controller → actuators
actuators → plant
plant → sensors
plant → metrics
```

When `observer.type == none` (ideal full state), still include the observer node with summary **“identity (true state)”** so the diagram stays comparable across matrix cells.

---

## 2. JSON schema (`runs[i].stack`)

```json
{
  "schema_version": 1,
  "topology": "closed_loop_sil",
  "nodes": [
    {
      "id": "controller",
      "kind": "controller",
      "title": "Hover LQR",
      "summary": "u = u_h − K(x̂ − x_r)",
      "badges": ["lqr_hover"]
    }
  ],
  "edges": [["observer", "controller"], ["controller", "actuators"]],
  "details": {
    "mission": { },
    "guidance": { },
    "sensors": { },
    "observer": { },
    "controller": { },
    "actuators": { },
    "plant": { },
    "metrics": { },
    "identity": { }
  }
}
```

### 2.1 Node fields

| Field | Type | Required |
|-------|------|----------|
| `id` | string | yes — stable key matching `details` |
| `kind` | string | yes — same as id for v1 |
| `title` | string | yes — short UI label |
| `summary` | string | yes — one line under the block |
| `badges` | string[] | no — e.g. `["linear_kf","pos","omega"]` |

### 2.2 `details.identity`

| Field | Source |
|-------|--------|
| `study_id` | study / manifest |
| `gallery_id` | gallery entry id (filled by gallery) |
| `seed` | study / manifest |
| `git_commit` | manifest `code_identity` if present |
| `config_hash` | manifest if present |
| `uavsim_version` | manifest / package |
| `vehicle_id` | vehicle YAML |
| `source_run` | run directory name |

### 2.3 `details.mission`

| Field | Notes |
|-------|--------|
| `mission_file` | Relative path if possible (`configs/missions/...`) |
| `name` | Mission YAML `name` if loaded |
| `frame` | e.g. NED |
| `n_waypoints` | count |
| `duration_s` | last wp time − first (if available) |
| `yaw_mode` | from guidance (duplicated for glance) |
| `waypoints_preview` | optional ≤9 `{t,x,y,z,yaw,label?}` |

### 2.4 `details.guidance`

| Field | Notes |
|-------|--------|
| `type` | `waypoints` / `hold` |
| `method` | `auto` / minsnap / interp |
| `yaw_mode` | constant / from_waypoints / path_tangent |
| `sample_dt_s` | |
| `fail_on_infeasible` | |
| `mission_file` | |

### 2.5 `details.sensors` / `details.observer`

| Field | Notes |
|-------|--------|
| `observer_type` | `none` / `partial_raw` / `linear_kf` / … |
| `channels` | list or null (= full / N/A) |
| `pos_sigma_m`, `vel_sigma_m_s`, `att_sigma_rad`, `omega_sigma_rad_s` | |
| `process_sigma` | |
| `seed` | observer seed |
| `notes` | human string, e.g. naive zeros unobserved states |

### 2.6 `details.controller`

Prefer **`nominal/controller_artifact.yaml`** when present; else study `controller:` block.

| Field | Notes |
|-------|--------|
| `type` | `lqr_hover` / `pid_cascade` |
| `frames` | from artifact if present |
| `u_hover` | list[4] |
| `gains` | LQR: `{K, Q_diag, R_diag}`; PID: kp/kd blocks |
| `design` | LQR poles if present |
| `vehicle_trim` | mass, arm, inertia snapshot if in artifact |
| `equation` | short string for UI caption |

### 2.7 `details.actuators`

| Field | Notes |
|-------|--------|
| `plant_mode` | `wrench` \| `motors` from `sim.plant` |
| `command` | `body_wrench` |
| `mixer` | layout, ct, cq when motors or always from vehicle propulsion |
| `motor_time_const_s` | |
| `omega_min_rad_s`, `omega_max_rad_s` | |
| `limits` | thrust/torque limits |

### 2.8 `details.plant`

| Field | Notes |
|-------|--------|
| `attitude` | `euler` \| `quat` |
| `plant_mode` | same as actuators |
| `state_dim_bus` | 12 (control bus) |
| `dynamics` | `rigid_body_6dof` |
| `vehicle` | mass, gravity, arm, inertia, limits |
| `aero` | full aero dict or flags `enabled` / key coeffs |
| `integrator` | dt, method, rtol, atol from sim |
| `notes` | e.g. “Aero defaults off (vacuum plant)” |

### 2.9 `details.metrics`

| Field | Notes |
|-------|--------|
| `position_bound_m` | from study metrics |
| `reported` | optional subset of run metrics (rmse_*, within_bound) if available at build |

---

## 3. Builder API (Python)

Module: `src/uavsim/viz/stack.py`

```python
def build_stack_from_run_dir(run_dir: Path | str, *, gallery_id: str | None = None) -> dict:
    """Assemble stack from study_config + controller_artifact + vehicle + mission."""

def build_stack_from_study_mapping(study: dict, *, vehicle: dict | None = None, ...) -> dict:
    """Config-only path for tests / offline enrich without timeseries."""
```

`run_to_gallery_entry` in `gallery.py` sets:

```python
entry["stack"] = build_stack_from_run_dir(run_dir, gallery_id=gid)
```

If build fails, set `stack: null` and do not break gallery generation.

Relativize absolute mission/vehicle paths to `configs/...` when under repo root.

---

## 4. UI (SPA)

| Item | Spec |
|------|------|
| Tab | After **Flight**, before **Estimation**: `{ id: "stack", label: "System" }` |
| Binding | Active run (same picker as Flight / Metrics) |
| Diagram | Horizontal (wrap on narrow) HTML/CSS blocks + arrows — no external diagram lib required |
| Interaction | Click node → detail panel below or side with title, summary, structured fields |
| Matrices | Render `gains.K` as HTML table; Q/R diag as vectors; PID gains as labeled lists |
| Empty | If `run.stack` missing: short message “Rebuild gallery for stack provenance” |
| Walkthrough | Optional 5th step or keep 4; do not force System into strip for Phase 1 |

Styles: match existing dark theme (`styles.css`). Accessible: buttons for nodes, `aria-selected` on active block.

---

## 5. Tests

| Test | Expectation |
|------|-------------|
| Unit: ideal LQR study config → stack | controller type lqr, observer none, plant wrench, edges present |
| Unit: GPS+IMU LQG study path or run dir | observer linear_kf, channels pos+omega |
| Unit: PID cascade | gains keys without requiring K |
| Unit: motors plant study if available | actuators plant_mode motors |
| Gallery entry | `stack` key present when building from a real run dir under `runs/` |

---

## 6. Docs sync

- Update `docs/showcase/UI_SPEC.md` § tabs + data contract for `runs[].stack`
- Link from `docs/showcase/README.md`
- This file is the schema source of truth for Phase 0–1

## 7. Later (not this branch slice)

- Mission `plant_fidelity` matrix
- Export hover \(A,B\) into `details.plant.linearization`
- Lazy `data/runs/<id>/stack.json` if payload grows
- Per-rotor thrust Flight overlay

---

**Last updated:** 2026-07-24 — Phase 0–1 contract for branch work.
