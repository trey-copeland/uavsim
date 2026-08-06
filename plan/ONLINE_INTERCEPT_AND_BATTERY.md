# Plan: Online intercept guidance + battery energy model

| Field | Value |
|-------|--------|
| **Status** | **Shipped on main** (merged PR #1) — L0–L4 capability, demo SPA + export, LIMITATIONS; teaching guides on `feature/tutorials` (T0 · ONLINE · ENERGY · PLUGIN · VEH-YAML) |
| **Goal** | Ship a **single-vehicle, online guidance** backend that pursues a **scripted target** via mid-sim replan, an **opt-in battery** model that never breaks existing studies, and a **live interactive demo** (GitHub Pages) |
| **Primary story** | Sized-up quadrotor, takeoff → aggressive intercept (**beyond hover-linear** attitude), **NDI only**, energy margin so the mission can fail honestly |
| **Airframe** | **Quadrotor only** (X layout as today). Not trirotor / multi-layout |
| **Audience** | Research users learning guidance extension; GNC peers evaluating online reference generation + energy |
| **Related backlog** | G-4/G-5 (registry-driven pipeline), **G-6** (`update` in closed loop), G-7 (non-waypoint family), battery gap |
| **Companion** | Hosting / teaching packaging: [`TUTORIALS.md`](TUTORIALS.md) |
| **Git** | Product epic merged via `feature/intercept-guidance-battery`; follow-on tutorials on `feature/tutorials` |

This document is the **implementation plan and product contract** for the intercept + energy + demo epic.

---

## 0A. Mission-feasibility gaps (close these to maximize success odds)

Ordered by **risk of “we built the plumbing and the chase still fails”**. Close high items **before** demo UI polish.

### P0 — Must specify and prove before declaring mission success

| # | Gap | Why it kills the mission | Plan closure |
|---|-----|--------------------------|--------------|
| **G1** | **Geometry & kinematics budget** under-specified | Capture ≤1 m with online lead-point only works if target speed, ownship T/W, range, and replan horizon are co-designed. Vague “hard flyby” → either trivial or impossible | **Lock a numeric mission brief** (§0A.1): initial geometry, target speed profile, max range, time budget, required peak horizontal accel. Validate with **open-loop kinematics** (point-mass double integrator + T/W limit) before NDI |
| **G2** | **Oracle ladder not in the plan as a gate** | Stacking G-6 + new vehicle + NDI + MEKF + battery + MC at once makes root-cause impossible | **Mandatory staged green gates** (§0A.2): each stage must capture before next complexity |
| **G3** | **NDI + large tilt + short-horizon \(x_r\)** interaction | NDI is memoryless; needs good `a_ref` / \(x_r\) rates. Replanned segments that are position-only or non-smooth → lag, overshoot, miss | Short-horizon builder must emit **full `SampledReference`** with \(p,v,\psi,\omega\)-consistent samples and **`a_ref`**; enforce min segment time / max snap; unit-test NDI on a static intercept segment first |
| **G4** | **Sense loop under large attitude** | Hover `linear_kf` unfit; stock MEKF omits thrust–tilt error coupling | **Filter acceptance tests**: under truth \(u\) and synthetic GPS+gyro at **large tilt** (beyond hover-linear), \(\hat p,\hat R\) errors stay within bounds that NDI can tolerate; land MEKF process-model fix before noisy success claim |
| **G5** | **G-6 plumbing + fixed-step + adapter rebind** | `update` exists but is not called; RK45 path has no replan hook | Phase A stub: replan changes hover setpoint and is **observable** in logs before intercept smarts |

### P1 — High likelihood of failure if deferred

| # | Gap | Why | Plan closure |
|---|-----|-----|--------------|
| **G6** | **Vehicle + NDI gains not co-tuned** | 1.5 kg / T/W 4–5 / \(\tau_\max\) / `max_tilt_rad` / \(k_R,k_\omega,k_p\) are interdependent | Tuning procedure: (1) hover hold on new vehicle, (2) step accel / large tilt command, (3) open intercept segment with truth state, (4) add filter. Document final gains in study YAML |
| **G7** | **Cone clamp vs large tilt** | NDI clamps virtual accel to `max_tilt_rad` (code caps below \(\pi/2\)). High tilt changes saturation behavior | Explicit **tilt budget** in mission brief; success needs **beyond-linear** achieved tilt (L0 ~55° is fine); fail recipe can demand more than authority |
| **G8** | **Replan on \(\hat x\) vs truth** | Noisy/lagged \(\hat p\) → wrong intercept point → miss even if control is fine | Default demo: estimate-based replan **after** filter is green; keep truth-replan debug flag; consider light **target-relative** residual if estimate bias dominates |
| **G9** | **Capture timing / “pass through”** | Min-range ≤1 m can be a glancing miss at high relative speed | Define success as min-range ≤1 m **and** optionally relative speed or dwell; or slow target enough that NDI can null range-rate near CPA |
| **G10** | **MC scatter vs success margin** | Aggressive MC on mass/I with thin margin → P(capture)≈0 and a sad demo | Size success recipe so **nominal is comfortable** (e.g. min-range ≪1 m); set MC σ so P(capture) is informative (e.g. 0.7–0.95), not 0 or 1; fail recipe separate |

### P2 — Product completeness (less likely to block first capture)

| # | Gap | Plan closure |
|---|-----|--------------|
| **G11** | Battery model coupling | Ship battery as **log + fail flag** first; do not couple thrust derate until intercept works |
| **G12** | Demo export (MC bands, dual case) | After deterministic success/fail + MC CSV/JSON envelopes exist |
| **G13** | Registry G-5 | Nice for tutorials; manual pipeline branch OK if intercept works |
| **G14** | Motors / aero plant | Wrench vacuum (or light aero) first; motors lag is a known NDI stress |
| **G15** | True IMU biases / multipath | Stretch; GPS pos already anchors \(p\) |

### 0A.1 Mission brief (L0 locked 2026-07-25)

| Quantity | Value | Notes |
|----------|-------|--------|
| Ownship start | \([0,0,3]\) NED | settle 1 s then transit |
| Target path | \(p=[20,-15+5t,3]\), \(v=[0,5,0]\) | `intercept_l0_target.yaml` |
| Target speed | **5 m/s** | +East flyby |
| CPA design | \(t=3\) s → target \([20,0,3]\) | ownship minsnap to CPA then ride-along to \(t=8\) |
| Capture radius | **1.0 m** | locked |
| Time budget | **8 s** | |
| Peak tilt (success L0) | **~55°** achieved | **beyond hover-linear** — sufficient; no drive to force ~90° |
| Success vehicle | `intercept_quadrotor` T/W≈**4.5**, \(\tau_\max=4\) | min_range **≈0.04 m** (truth NDI) |
| Fail vehicle | `intercept_quadrotor_underpowered` T/W≈**1.15** | min_range **≈3.8 m** (miss) |
| Sensor | Online hero: **MEKF** + `pos`/`omega` | L2 green on branch |
| MC online | **P(capture)≈0.28** (500 trials) | plant scatter + estimate replan |

**L0 gate:** green (open-loop). **L1–L4:** green enough to ship capability (online pursue, MEKF, energy log fail, MC).

### 0A.2 Oracle ladder (definition of “green”)

Each step must achieve **min-range ≤ 1 m** (or explicit waiver) before the next:

| Stage | State to control | Guidance | Observer | Pass criterion |
|-------|------------------|----------|----------|----------------|
| **L0** | truth | offline open-loop intercept path (waypoints) | none | NDI + vehicle can fly a precomputed intercept |
| **L1** | truth | **online** replan (G-6) | none | capture with moving target |
| **L2** | \(\hat x\) | online | MEKF improved + GPS+IMU | capture under noise |
| **L3** | \(\hat x\) | online + battery log | same | success + energy-fail recipes |
| **L4** | \(\hat x\) | + MC | same | P(capture) in target band; export bands |

Do **not** start Pages UI until **L2** is green. Do not tune MC until **L3** nominal margin is known.

### 0A.3 Reference quality checklist (replan output)

Every replan `SampledReference` must:

1. Start from **current** ownship \(p\) (truth or \(\hat p\)) with continuous \(v\) handoff if possible.  
2. Provide dense samples with **`a_ref`** for NDI feedforward.  
3. Avoid sub-dt or sub-~0.2 s horizons that chatter.  
4. After capture: switch to track/hold target without discontinuous jumps.  
5. Log replan times, \(p_t^\star\), and commanded horizon for debug.

---

## 0. Locked product decisions (2026-07-25)

| Topic | Decision |
|-------|----------|
| Airframe | **Existing X-quadrotor family**, **sized up** (higher mass class + higher thrust/torque authority) so aggressive intercept is plausible |
| Attitude regime | Exceed the **hover / small-angle linear region** (not a hard ~90° requirement). Plant **`sim.attitude: quat`**; SO(3)-aware path. L0 success already peaks ~**55°** tilt |
| Control law | **NDI only** for this mission (`ndi_cascade`). No LQR/PID portfolio matrix for intercept v1 (hover linearization / small-angle cascade not the teaching point) |
| Actuation interface | **Body wrench** \(u=[F,\tau]\) as today; motors plant optional for fidelity, not a new control interface |
| Beyond wrench | **Out of this epic.** Future plans (flex, multi-airframe, motor-level NDI) own “extending past wrench-only” |
| Multi-vehicle plant | **No** — target is a scripted trajectory |
| Done means | **Code + runnable studies + interactive demo live on GitHub Pages + README / developer docs / LIMITATIONS synced** — not “merge only” |

---

## 1. Product intent

### 1.1 One-sentence story

> A more powerful quadrotor takes off, **replans \(x_r\) online** toward a flying target using NDI through large attitude, and the demo shows whether **energy and capture** succeed or fail.

### 1.2 Why this (not multi-vehicle)

| Choice | Rationale |
|--------|-----------|
| **No multi-agent plant** | Out of core scope; not required |
| **Scripted target** | Open-loop NED path; ownship is the only closed-loop body |
| **Online ownship reference** | Real `GuidanceBackend.update` (G-6) |
| **Battery opt-in** | Endurance story without breaking default studies |
| **NDI + quat** | Beyond-linear attitude; honest law for the envelope |

### 1.3 Acceptance (MVP)

| Surface | Requirement |
|---------|-------------|
| **Vehicle** | Tutorial/demo quadrotor YAML: larger mass, higher \(F_\max\), higher \(\tau_\max\), propulsion sized for hover margin under aggressive \(F\) |
| **Guidance** | Backend e.g. `intercept_pursue`: offline `plan` + in-loop `update` |
| **Sim** | Closed-loop **invokes** `guidance.update` on a schedule (fixed-step when online) |
| **Controller** | **`ndi_cascade` only** for intercept recipes; still wrench out |
| **Plant** | Prefer **quat** (+ optional motors/aero later); document choices in study YAML |
| **Sensing** | **GPS + IMU-style** partial measurements in the loop (not full-state truth for the hero demo) |
| **Observer** | **Not hover `linear_kf` as the hero** for beyond-linear intercept — see §3.4. Prefer **MEKF path + planned filter upgrades** so NDI flies on \(\hat x\) |
| **Target** | Time-parameterized path; logged for viz (ownship + target) |
| **Battery** | Optional; default off → prior studies unchanged |
| **Metrics** | Capture success = min range to target **≤ ~1 m** (config `capture_radius_m`); time-to-capture; SOC / energy; energy_depleted |
| **Studies** | **Nominal success** + **nominal fail** (geometry/energy/authority) + **MC** on the success recipe (and optionally fail) |
| **MC** | Plant (and optional battery) scatter; report **P(capture)**, min-range distribution; demo viz with **toggleable confidence bands** (prefer **2D** N–E / N–up projections) |
| **Interactive demo** | Live on GH Pages: 3D path, attitude, **scrub + play**, battery, energy series, **success + fail** cases, **MC bands** (see §5) |
| **Tests** | Predict/replan unit; closed-loop intercept; regression without battery |
| **Docs** | README blurb, guidance.md, vehicles.md, LIMITATIONS, tutorial/demo index |

### 1.4 Explicit non-goals (v1)

- Trirotor / hex / layout plugins  
- Multi-vehicle dynamics  
- Live target sensing / target state estimation  
- Full electrochemical battery  
- LQR/PID intercept law matrix  
- Motor-level or non-wrench control interfaces  
- Replacing hold/waypoints defaults  
- Full portfolio estimation matrix rebuild  

---

## 2. Vehicle: sized-up quadrotor

### 2.1 Intent

Default 500 g class + heritage limits may **saturate** before a large-attitude intercept closes. Demo vehicle should feel like a **higher-thrust research / racing-scale** plant still modeled as X-quad.

### 2.2 Baseline concept: “intercept class” X-quad (~1.5 kg)

Heritage default is a **500 g class** teaching craft: \(m=0.5\), \(L=0.25\) m, \(F_\max = 2mg\) (T/W = 2), \(\tau_\max=1\) N·m. That is fine for figure-eights; it is **marginal** for a hard intercept (large tilt needs \(F \gtrsim mg/\cos\theta\) plus closing accel; MC mass-up trials eat margin).

**Proposed demo vehicle** (tune after first closed-loop cuts; numbers are a starting contract, not CAD truth):

| Param | Default 500 g | **Intercept class (target)** | Why |
|-------|---------------|------------------------------|-----|
| `vehicle_id` | `default_quadrotor` | `intercept_quadrotor` | Separate YAML; no silent default change |
| `mass_kg` | 0.5 | **~1.5** | Reads as a small research / heavy FPV-ish platform; MC σ on mass is meaningful in newtons |
| `arm_length_m` | 0.25 | **~0.30–0.35** | Slightly longer arms → torque from differential thrust without absurd ω |
| `inertia` ixx/iyy / izz | 0.0075 / 0.013 | **Scale ~ \(m L^2\)** (e.g. ixx≈0.04, izz≈0.07 order-of-mag — fit in impl) | Keep angular dynamics plausible |
| `thrust_max_n` | 9.81 (T/W = 2) | **T/W ≈ 4–5** → \(F_\max \approx (4\text{–}5)\,mg\) ≈ **60–75 N** at 1.5 kg | Sustained large tilt + horizontal accel for intercept; MC mass +% still flyable on success recipe |
| `torque_max_nm` | 1.0 | **~3–5** | Fast attitude for aggressive intercept under NDI |
| `propulsion` | hover ω ~600 rad/s | Raise \(c_T\) and/or \(\omega_\max\) so **wrench demands are achievable** if `plant: motors` later | Wrench plant can ship first |
| `battery` | off | **On** for demo; capacity ~ short intercept (tens of seconds), two sizes for success vs energy-fail | SOC story |
| NDI `max_tilt_rad` | often ~1.0 in existing studies | **Raise enough for beyond-linear tilt** (L0 uses 1.45; not a ~90° mandate) | Room above hover-linear |

**Why not keep 0.5 kg and only raise T/W?** Viable fallback (T/W 4–5 on the small craft works in SIL). Prefer **~1.5 kg** so: (1) energy numbers feel mission-like, (2) MC absolute force scatter is less toy-scale, (3) README story is “heavier intercept platform,” not “same microquad with cheat limits.”

**Why not multi-kg / 5 kg?** Bigger plant needs more sim-time / gain retune; 1–2 kg is enough authority narrative without becoming a different product.

Ship as `configs/vehicles/tutorials/intercept_quadrotor.yaml`. **Do not** change default 500 g semantics for existing studies.

### 2.2b Capture definition (locked direction)

```text
success ⇔  min_t  ‖ p_ownship(t) − p_target(t) ‖  ≤  r_capture
r_capture  ≈  1.0 m   (config: capture_radius_m; demo copy says “order of a meter”)
```

Target is a **point-mass reference** (scripted), not a second rigid body.

### 2.3 Control / plant pairing

```yaml
controller:
  type: ndi_cascade
  # gains tuned for this vehicle + mission
sim:
  attitude: quat
  plant: wrench   # or motors once allocation margin verified
```

If NDI + large tilt is unstable with motors lag, document and ship **wrench** first; add motors as stretch.

---

## 3. Architecture

### 3.1 Data flow

```text
Mission config
  ├─ target: ReferenceTrajectory  (open-loop; fixed at prepare)
  └─ intercept policy: replan period, lead time, capture radius, …

prepare_study / plan()
  └─ seed ownship x_r (takeoff / climb)

Closed-loop step t_k  (fixed-step when guidance_loop active)
  ├─ target.evaluate(t_k) → p_t, v_t
  ├─ predict p_t* at t + t_lead
  ├─ guidance.update(...) → new PlanResult | None → rebind x_r
  ├─ NDI(x̂ or x, x_r) → u wrench
  ├─ plant (quat)
  └─ battery.integrate(P(u,…), dt) if enabled
```

**Invariant:** Controllers stay wrench-primary; guidance never imports control; viz reads artifacts only.

### 3.2 Gaps to close

| Piece | Today | Required |
|-------|--------|----------|
| `GuidanceBackend.update` | Exists; unused | Intercept implements replan |
| Closed-loop | Offline reference only | `guidance_loop` + rebind |
| Adapter | Single ref | Mutable current ref |
| Pipeline guidance | hold \| waypoints | Intercept config (+ prefer G-5 registry) |
| Fixed-step | motors/observer/quat | Also when online guidance |
| Battery | Absent | Optional nested model |
| Demo UI | Showcase flight scrub only | Extract + battery/energy + **play** |

### 3.3 Import rules

1. `control` ↛ `guidance`  
2. `guidance` → `reference`, `vehicles`, state arrays only  
3. Battery: vehicle params + sim-side integrator  
4. Demo UI: pure consumer of run/demo JSON (showcase pattern)

### 3.4 Sensing & estimation (GPS + IMU realism)

**Product intent:** the intercept demo should be driven off a **realistic sense stack**, not ideal full-state. In this codebase that maps to the existing teaching story:

| Layer | Intercept demo choice |
|-------|------------------------|
| Measurements | **`channels: [pos, omega]`** — GPS-like position + gyro rates (portfolio “GPS + IMU”) |
| Optional later | add `vel` if we model GPS velocity; **not** required for v1 |
| Control bus | NDI on **\(\hat x\)** (same as other KF→NDI studies) |
| Not the hero | `observer: none` (truth) — keep only as optional “oracle upper bound” toggle |

#### Will existing `linear_kf` work?

**Not as the honest primary filter for this mission.**

| Fact | Implication for beyond-linear intercept |
|------|----------------------------------------|
| `linear_kf` predict uses **hover \(A,B\)** (`hover_linearization`) | Process model is small-angle / hover; large tilt + aggressive \(u\) is **outside the filter model** the same way it is outside LQR |
| State is **Euler 12** with linear attitude error | Large tilt: Euler linearization and hover thrust-tilt map are the wrong geometry |
| GPS+IMU + `linear_kf` **does** work on figure-eight portfolio cells | Those missions stay nearer hover-linear regime; **not** a transfer certificate to intercept |
| NDI needs usable \(\hat p, \hat v, \hat R, \hat\omega\) | A bad \(\hat x\) under large attitude will look like “NDI failed” when the filter did |

**Verdict:** keep `linear_kf` as a **negative / teaching contrast** if useful (“hover KF on aggressive intercept”), **not** as the ship path for the success recipe.

#### What about existing `mekf`?

Better starting point than `linear_kf` for large attitude:

| MEKF strength | MEKF limit (LIMITATIONS / EST-*) |
|---------------|-----------------------------------|
| Multiplicative / error-state attitude; nominal quat integration with thrust in inertial frame | Discrete error \(F\) is **simplified** — **thrust–tilt coupling** \(\delta\dot v \leftarrow -R[0,0,-F/m]\times\delta\theta\) **omitted** (hover-teaching MEKF) |
| Supports partial channels (`pos`, `omega`, …) | Not full IMU physics (biases, scale factors) — **EST-8** backlog |
| Outputs Euler-12 \(\hat x\) for NDI | Still a research SIL filter, not flight EKF |

**Verdict:** **MEKF + GPS pos + gyro is the right family** for the hero path, but we should **plan to extend** the estimation surface so the filter is not knowingly crippled for the attitude regime we advertise.

#### Planned estimation work (this epic or tightly coupled PR)

Priority order:

1. **Wire intercept studies to partial GPS+IMU + observer → NDI** (not truth).  
2. **Hero observer = `mekf`** (or successor id) with `channels: [pos, omega]`.  
3. **Extend MEKF (or add `mekf_intercept` / improved error-state)** at least:
   - Include **thrust-tilt / attitude→velocity** coupling in the error-state process model (close the documented MEKF gap for aggressive flight), **and/or**
   - Time-varying \(F\) consistent with current \(R, F_{\mathrm{thrust}}\) used in predict.  
4. **Honest LIMITATIONS:** still not random-walk biases / multipath unless we explicitly add a thin bias state later (stretch).  
5. Optional contrast study: same mission + `linear_kf` to show hover-KF breakdown (great teaching; not required for Pages hero if noisy).

**True IMU physics (accel aiding, bias RW)** remains EST-8-class stretch unless intercept MC is unusable without it; GPS position updates already anchor \(p\) so pure-gyro attitude integration + MEKF may suffice for SIL demo if coupling is fixed.

#### Guidance `state_source`

Online replan should default to **estimate** (`state_source: estimate`) for the realistic-sense story; truth-based replan only for debugging / oracle.

---

## 4. Online guidance design

### 4.1 MVP algorithm

Constant-velocity **lead-point intercept** + short-horizon replan:

1. Evaluate target; CV predict \(p_t^\star = p_t + v_t t_{\mathrm{lead}}\).  
2. Rebuild short `SampledReference` from current ownship position toward \(p_t^\star\).  
3. Yaw: path tangent or face target bearing.  
4. Capture when \(\|p - p_t\| < r_{\mathrm{cap}}\); then hold/track target open-loop.  
5. Offline `plan()`: takeoff/climb seed only.

### 4.2 Config sketch

```yaml
vehicle: configs/vehicles/tutorials/intercept_quadrotor.yaml

controller:
  type: ndi_cascade
  # ...

guidance:
  type: intercept_pursue
  seed:
    type: waypoints
    mission_file: configs/missions/tutorials/intercept_takeoff.yaml
  target:
    type: waypoints
    mission_file: configs/missions/tutorials/intercept_target_flyby.yaml
  replan_period_s: 0.2
  lead_time_s: 1.5
  capture_radius_m: 1.0
  horizon_s: 3.0
  method: interp
  yaw_mode: path_tangent
  state_source: truth
  fail_on_infeasible: false

sim:
  attitude: quat
  plant: wrench
```

### 4.3 G-6 plumbing

- `PreparedStudy` keeps backend + mission + **mutable reference cell**.  
- `simulate_closed_loop(..., guidance_loop=...)` on fixed-step: replan → rebind adapter.  
- Log replans + target timeseries for the demo.  
- Prefer G-5 registry wiring if cheap; else manual branch then clean up.

### 4.4 Prediction helpers

Pure functions under `uavsim/guidance/intercept/` — unit-tested without plant.

---

## 5. Interactive demo (not Markdown-only)

Markdown developer notes are **supporting**. The **acceptance demo** is interactive and **hosted live** (GitHub Pages), similar in spirit to the portfolio showcase.

### 5.1 UX requirements

| Feature | Notes |
|---------|--------|
| **Case switch** | **Successful intercept** vs **unsuccessful** (nominal deterministic runs; clear labels) |
| **3D flight path** | Ownship + **target**; capture sphere/radius cue (~1 m) optional |
| **Attitude view** | Vehicle attitude pane (showcase dual-pane pattern) |
| **Time scrubber** | Drag through history |
| **Play / pause** | Auto-advance (new vs current showcase) |
| **Battery indicator** | SOC vs time index |
| **Energy time series** | Power and/or SOC; scrub-synced |
| **MC confidence** | Toggleable **percentile / confidence bands** on trajectories — **primary in 2D** (e.g. North–East top-down and/or North–Up), optional 3D later if cheap; show **P(capture)** and min-range histogram or summary |

### 5.2 Engineering approach

1. **Extract** reusable Flight-style components from `docs/showcase/` (Plotly 3D path, attitude pane, time index state) into a shared module used by:
   - portfolio showcase (optional later refactor), and  
   - **intercept demo** page (primary).  
2. Prefer **thin demo app** under e.g. `docs/demos/intercept/` (or `docs/tutorials/intercept/app/`) with its own `data/` built from tutorial studies — **do not** require full estimation-matrix gallery rebuild.  
3. Data pack: timeseries (ownship \(x\), \(u\), target \(p\), SOC, power), metrics JSON, stack summary optional.  
4. Build script: `uv run …` simulate tutorial studies → export demo JSON (mirror showcase export pattern at smaller scale).

### 5.3 Hosting

- GitHub Pages serves the demo (same project pages site or path).  
- README links **Demo** prominently once live.  
- Static assets only (no server-side sim in browser for v1).

---

## 6. Battery / energy (additive, non-breaking)

### 6.1 Principles

1. Default **off** — no battery key → bit-compatible studies.  
2. Explicit optional `BatteryParams` (`extra="forbid"` preserved).  
3. Side integrator on \(u\) / ω; not a required plant state in v1.  
4. LIMITATIONS: **power proxy**, not a lab cell model.

### 6.2 Schema sketch

```yaml
battery:
  enabled: true
  capacity_wh: 40.0
  initial_soc: 1.0
  model: hover_scaled
  hover_power_w: 200.0      # scale with sized-up vehicle
  thrust_power_exp: 1.5
  idle_power_w: 10.0
  empty_behavior: flag
```

### 6.3 Metrics

| Metric | Meaning |
|--------|---------|
| `intercept_success` | Range criterion |
| `time_to_capture_s` | First capture or NaN |
| `soc_final` / `energy_used_wh` | Endurance |
| `energy_depleted` | SOC hit 0 before tf |

### 6.4 Regression

Existing YAMLs without `battery` load and run as today. No forced SOC columns on old reports.

---

## 7. Studies / recipes + Monte Carlo

### 7.1 Deterministic recipes

| Recipe | Intent |
|--------|--------|
| `intercept_takeoff` mission | Pad → climb |
| `intercept_target_flyby` | Moving target that forces large ownship tilt if closing hard |
| `intercept_success` | NDI + sized quad + battery margin → **min range ≤ ~1 m** |
| `intercept_fail` | Unsuccessful: e.g. undersized battery, reduced \(F_\max\), and/or faster/harder target geometry so capture fails honestly |
| **No** LQR/PID intercept matrix | NDI only |

Tune so **success is impressive but fair**; fail is intentional and labeled.

### 7.2 Monte Carlo (in scope for ship)

| Item | Plan |
|------|------|
| **Base study** | MC attached to **success** geometry (primary); optional second MC on fail recipe |
| **Perturb** | Existing MC: mass, inertia, arm (± relative/absolute as today); optional propulsion / battery capacity scatter if cheap |
| **Controller** | Default `redesign_controller: false` — **NDI gains fixed on nominal** vehicle (robustness story: fixed law, uncertain plant). Document like other MC demos |
| **n trials** | Demo-friendly (e.g. 50–200); CI smoke with small N |
| **Per-trial metrics** | `intercept_success` (bool), `min_range_m`, `time_to_capture_s`, `soc_final`, saturated flags |
| **Aggregate** | **P(capture)**, mean/percentile min-range, optional energy stats |
| **Viz export** | Trial trajectories (or quantile envelopes at sample times) for **2D confidence bands**; summary JSON for demo UI |

### 7.3 Confidence-band visualization (demo)

- **Toggle** “MC bands” on/off.  
- **2D first:** e.g. North–East and/or horizontal range vs time; band = percentile envelope (e.g. 5–95% or ±1σ if Gaussian summary).  
- Nominal success path as bold centerline; target path solid.  
- Capture: show **circle of radius \(r_{\mathrm{capture}}\)** in top-down view when helpful.  
- KPI chip: **P(success | MC)** next to nominal success/fail switch.  
- 3D cloud of all trials is optional stretch (can be heavy); bands in 2D are the clarity win.

---

## 7b. Capture metric (detail)

```text
r_i(t) = ‖ p_own(t) − p_target(t) ‖
min_range = min_t r_i(t)
intercept_success = (min_range ≤ capture_radius_m)   # default 1.0 m
```

Log full `range_m(t)` for plots. Point-mass target; no airframe size on target.

---

## 8. Tests

| Layer | Cases |
|-------|--------|
| Unit predict / backend / battery | As before |
| Integration | Success captures; energy_fail; fixed-step + quat + NDI |
| Regression | Default studies without battery |
| Demo export smoke | Builder produces JSON keys the UI expects |

---

## 9. Implementation phases

### Phase A — G-6 plumbing

Stub replan + mutable reference + fixed-step hook + tests.

### Phase B — Intercept + sized quadrotor + NDI + sense loop

Backend, missions, success study, quat + `ndi_cascade` on \(\hat x\), GPS+IMU channels, MEKF (or improved) in loop, capture metrics.

### Phase B2 — Estimation extension for large attitude

MEKF error-state coupling (thrust-tilt / \(R\)-dependent \(F\)); regression that hover figure-eight GPS+IMU paths still pass; intercept success under noise.

### Phase C — Battery

Opt-in model, SOC logs, fail study (energy and/or authority), LIMITATIONS.

### Phase C2 — Monte Carlo

Success-study MC config; trial metrics; aggregate P(capture); export envelopes for demo.

### Phase D — Interactive demo + extract UI

Shared flight/scrub/play; battery + energy; **success/fail switch**; **MC band toggle (2D)**; Pages data.

### Phase E — Docs sync + ship gate

README, developer guides, EXTENSIBILITY_TODO; **Pages live**.

### Phase F — Stretch

Motors plant; auto lead-time; PN; thrust derate at empty; 3D MC cloud; full showcase refactor onto extracted components.

---

## 10. Risks

| Risk | Mitigation |
|------|------------|
| Large tilt + NDI saturates | Size thrust/torque up; tune gains; shorten horizon; verify on quat plant |
| Replan vs RK45 | Fixed-step whenever online guidance |
| Demo scope creep to full showcase | Single-mission data pack; extract only Flight-like pieces |
| Battery oversold | LIMITATIONS proxy language |
| Users expect second vehicle | Docs + UI label “scripted target” |

---

## 11. Exit criteria (epic **done**)

- [x] G-6 online replan works for intercept studies (`intercept_pursue`)  
- [x] Sized quadrotor + NDI + quat + **MEKF GPS+IMU** intercept success (`intercept_online_success`)  
- [x] Hero filter is **MEKF** (not hover-`linear_kf`); thrust–tilt MEKF polish still open  
- [x] Replan `state_source: estimate` on hero recipe  
- [x] Unsuccessful recipes: underpowered L0 miss; energy_fail depletes SOC  
- [x] Battery optional; defaults unbroken  
- [x] **MC** on online hero: P(capture)≈0.28 @ 500 trials; bands exportable  
- [x] Unit tests for G-6 / predict / battery  
- [x] Interactive demo SPA (R3) in-repo; **re-export pack from online MC** (`p_capture≈0.28`)  
- [x] **Merged to main** + Pages workflow publishes `/` + `/intercept/`  
- [x] Developer docs + LIMITATIONS sync  
- [x] Tutorial track (companion): T0, T-GUIDE-ONLINE, T-ENERGY, T-GUIDE-PLUGIN, T-VEH-YAML — see [`TUTORIALS.md`](TUTORIALS.md) 

---

## 12. PR sequence

1. G-6 plumbing + stub  
2. Intercept backend + sized vehicle + NDI success study + 1 m capture metric  
3. Battery + fail study  
4. MC + envelope export  
5. Demo UI (play, battery, energy, success/fail, MC bands) + Pages  
6. Docs / README / backlog  

No trirotor or multi-layout work in this epic.
