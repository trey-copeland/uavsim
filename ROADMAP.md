# ROADMAP — `uavsim` / quadrotor-sim

**Status:** Active  
**Last updated:** 2026-07-20  
**Normative detail:** [`SPEC.md`](SPEC.md) (requirements, stories, acceptance) · [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) (how) · [`GROK.md`](GROK.md) (process) · [developer hub](docs/developer/README.md)

This roadmap is the **sequencing and prioritization** view. It does not replace the SPEC.

---

## 1. Problem / opportunity

| | |
|--|--|
| **Problem** | ME590 domain work is strong but trapped in a private MATLAB tree with architectural debt — not a public GNC portfolio piece. |
| **Opportunity** | Ship `uavsim`: modern SIL GNC + systems demos, with a clear path to controller export and HIL compare. |
| **North-star workflow** | Vehicle → dynamics → SIL design/analyze → **export** → **HIL** → **compare** |

---

## 2. Success criteria

### Core complete (portfolio + systems)

Ship when SPEC §17 holds, especially:

- Clone → SIL simulate + MC smoke on WSL  
- LQR tracks a gentle mission; artifacts + metrics  
- Containers + sharded MC  
- Extensibility story (controller + guidance backend)  
- **Should:** second controller, **export**, **compare** two SIL runs, SIL plant adapter  

**Not required for core:** live HIL hardware, firmware flash, certification claims.

### Long-term product success

- Same plant/metrics for SIL and HIL  
- Fast SIL↔HIL (or SIL↔SIL) visual/metric compare  
- Navigation beyond waypoints without rewriting the sim loop  

---

## 3. Current status

| Area | State |
|------|--------|
| Process docs (`GROK`, `AGENTS`) | **Done** |
| Product SPEC v0.2 | **Done** |
| Architecture v0.4 | **Done** |
| License / README / git baseline | **Done** |
| Repo code skeleton (`uv`, `src/uavsim`, tests, CI) | **Done** (Phase 0) |
| Phase 1 SIL physics loop | **Done** |
| Phase 2 Guidance + control interface | **Done** |
| Phase 3 Robustness (local MC + study/report) | **Done** |
| Phase 4 Systems (Docker + sharded MC) | **Done** |
| Phase 5 Workflow polish (export / compare / 2nd controller) | **Done** |
| Phase 5b Visualization pack (S5 / §11A V1–V8) | **Done** |
| Portfolio advertise (Pages + LinkedIn) | **Done** |
| Phase 5c Attitude / plant fidelity (quaternions → richer missions) | **Done** (optional native 13-state export still open) |
| Phase 5d Observer-in-the-loop (KF/EKF) | **Done** (`linear_kf`, `mekf`, partial channels, `x_hat` log) |
| HIL test rig (hardware order/build) | **In progress (parallel, long lead)** |
| Next SIL: motors / mixer (D-7, D-8) | **Now** (Track A) |
| Phase 6 nav / Phase 7 HIL software | **Not started** (nav after plant fidelity as needed; HIL when rig ready) |

---

## 4. Delivery phases

Phases are **capability gates**, not calendar dates. Prefer finishing a gate’s exit signals before starting the next large chunk (small spikes OK).

| Phase | Name | Epics | Exit signals (short) | Priority |
|-------|------|-------|----------------------|----------|
| **0** | Stand-up | — | `uv` package `uavsim`, pytest, ruff, CI stub, thin CLI | Done |
| **1** | SIL physics loop | A, C | Vehicle + dynamics + LQR + trivial reference + run dir + `simulate`; SIL adapter seam | Done |
| **2** | Guidance + control interface | B, C | Waypoints, interp/min-snap, feasibility, registries, ≥3 missions | Done |
| **3** | Robustness | C, F | Local MC, `study`, seed-stable smoke, plots-as-consumer | Done |
| **4** | Systems | F | Docker study + sharded MC assemble | Done |
| **5** | Workflow polish | D, E-SIL | **Export** + **`compare`** two SIL runs; second controller if not done | Done |
| **5b** | Visualization | S5 | Interactive 3D + MC pack + showcase | Done |
| **5c** | Attitude & plant fidelity | A+ | Quaternion kinematics + error-state control; large-attitude demo; `DynamicsModel` for flex/motors | **Done** |
| **5d** | Observer-in-the-loop | C+, E | Noisy measurements + filter (KF/MEKF) feeding control; ideal full-state remains default | **Done** |
| **—** | Plant fidelity (motors) | A+ | Motor dynamics + mixer (D-7, D-8) | **Now** |
| **6** | Nav expansion | B+ | First non-waypoint guidance | After motors/flex or when mission design needs it |
| **7** | HIL / PIL | E | Fixed-step + transport + SIL↔HIL via export/compare | Parallel with rig build; software when rig ready |

Detail and MoSCoW: SPEC §6, §19. Module map: ARCH §3, §16. Backlog IDs: [`docs/developer/EXTENSIBILITY_TODO.md`](docs/developer/EXTENSIBILITY_TODO.md).

---

## 5. Now / next / later

### Parallel tracks (2026-07 decision)

| Track | Cadence | Why |
|-------|---------|-----|
| **A — SIL platform** | Active coding now | Advance modeling (quats → motors/flex) without waiting on hardware |
| **B — HIL test rig** | Long lead (order, build, wire) | myDAQ, sensors, frame; blocks Phase 7 **hardware** validation but not SIL |

Do **not** stall Track A on Track B. Keep HIL **seams** (fixed-step, I/O schemas) thin until the rig exists.

### Now (Track A — SIL)
1. Keep showcase / gentle figure-eight as regression baseline.  
2. **Motor dynamics + mixer** (D-7, D-8) — next plant fidelity step after 5c/5d.  
3. Optional: native 13-state export polish (not blocking).

### Next (Track A, still SIL)
1. Flexible / elastic plant spike (V-7 → lumped modes).  
2. Phase 6 non-waypoint guidance if mission design needs it more than plant fidelity.  
3. Deeper estimation (real IMU models, sensor fusion polish) as HIL approaches.

### Later / when rig is ready (Track B + Phase 7)
1. Companion project: NATS/MQTT, high-rate accels, ESC RPM (COMM-*, INSTR-1).  
2. Phase 7 fixed-step plant + transport + SIL↔HIL compare.  
3. Multi-airframe families (V-8, D-12, S-7) once mixer + dynamics protocol exist.

### 5.1 Phase 5c — attitude & plant fidelity (detail)

**Goal:** Stop treating ZYX Euler + small-angle LQR as the ceiling for *which missions we can model*. Quaternions (or equivalent SO(3) kinematics + error-state control) come **before** waiting on the HIL bench.

| Slice | Exit signals | Backlog | Status |
|-------|--------------|---------|--------|
| **5c.1** Plant kinematics | Unit-quat + renorm; open-loop Euler parity | D-10 | **Done** |
| **5c.2** Control / metrics | SO(3) error in LQR/PID/metrics | D-10 | **Done** |
| **5c.3** Optional quat plant + mission stress | `sim.attitude: quat`; aggressive elevated F8 demo | D-10, configs | **Done** |
| **5c.4** Extensibility | `DynamicsModel` injection (D-3) | D-3 | **Done** |

**Then (still Track A):** **5d observer** → motors/mixer → flexible body; **not** blocked on Phase 7 hardware.

**Why not HIL-first:** Rig procurement/build is multi-week; SIL can ship mission envelope + model fidelity + estimation seams in that window.

### 5.3 Phase 5d — observer-in-the-loop (scoped; was deferred)

**Previously:** SPEC listed “sensor models and EKF” as deferred; only C-9 (partial-state bus) existed as a thin TODO.  
**Now in product scope** for SIL-before-HIL: control must be able to run on **estimates**, not only ideal full state.

| Slice | Exit signals | Backlog |
|-------|--------------|---------|
| **5d.1** Measurement models | Configurable noise / partial outputs on `MeasurementBus` (pos, IMU-like rates, etc.) | C-9, EST-1 |
| **5d.2** Filter protocol | `StateObserver` (predict/update) pluggable in closed-loop between plant and controller | EST-2 |
| **5d.3** Reference KF/EKF | At least one working filter (e.g. linear KF on pos/vel **or** simple MEKF/error-state EKF on attitude) | EST-3 |
| **5d.4** Study switch | `sim.observer: none \| …` — default `none` (full-state) preserves all goldens | pipeline |

**Dependency:** Prefer finishing 5c.4 (`DynamicsModel`) so plant and process-noise models share one f(x,u). Observer work can start as soon as MeasurementBus stays the control input (already true).

### 5.2 Multi-airframe & lab research (after 5c foundation)

Track against [`docs/developer/EXTENSIBILITY_TODO.md`](docs/developer/EXTENSIBILITY_TODO.md) and [`docs/developer/airframes.md`](docs/developer/airframes.md).

| Theme | Intent | Notes |
|-------|--------|-------|
| Motor / mixer foundation | First-order motor states + allocation | D-7, D-8 — after D-3 |
| Flexible body | Lumped elasticity / arm modes | V-7; needs extra states on DynamicsModel |
| Pluggable airframe families | Tilt-rotor VTOL, hybrids, etc. | V-8, D-12; after mixer |
| HIL companion + rig | myDAQ, high-rate sensors, NATS/MQTT | D-11, COMM-*, INSTR-1; Track B |
| Comparative MC | Airframe selector in studies | S-7 |

**Priority alignment:** **quaternions + dynamics protocol first** → motors/flex → multi-airframe → full HIL software. Preserve MC, export/compare, and viz; rebaseline soft metrics when the state layout changes.

---

## 6. Milestone checklist

Use as a living board (check off in PRs or edit this file).

### M0 — Skeleton
- [x] `pyproject.toml` + `src/uavsim` installable  
- [x] `pytest` + `ruff` (+ CI workflow stub)  
- [x] `uavsim --help` (or equivalent)  
- [x] Empty package modules match ARCH names  

### M1 — First SIL demo
- [x] Default vehicle config  
- [x] Nonlinear dynamics + hover LQR  
- [x] Minimal reference + closed-loop sim  
- [x] Run directory with metrics  
- [x] Unit tests: trim / basic invariants  

### M2 — Guidance portfolio path
- [x] Waypoint missions (hover, gentle, aggressive)  
- [x] Interp + min-snap (+ auto policy Should)  
- [x] Feasibility warnings on bad auto-yaw case  
- [x] Guidance stub backend test (non-waypoint shape)  

### M3 — MC + study CLI
- [x] `uavsim study` with seed reproducibility  
- [x] Trial table + summary schema  
- [x] Single-run `report` / figures consumer  

### M4 — Systems demo
- [x] Container runs a documented study  
- [x] Sharded MC merge matches local (soft tolerance)  

### M5 — Workflow without hardware
- [x] Controller export round-trip  
- [x] `uavsim compare` two SIL runs  
- [x] Second controller comparison study (Should)  
- [x] **→ declare core complete** when SPEC §17 satisfied (SIL path + systems + export/compare)  

### M5b — Visualization pack (SPEC §11A)
- [x] V1 Playback + path trail (interactive HTML)  
- [x] V2 Dual-run 3D overlay  
- [x] V3 Time-synced strip charts  
- [x] V4 Saturation / limit shading on \(u(t)\)  
- [x] V5 MC CDF + param-vs-RMSE scatter  
- [x] V6 Feasibility callouts in report  
- [x] V7 `uavsim report --interactive`  
- [x] V8 3D still PNG export  

### M5c — Quaternion attitude & plant fidelity (**done**; optional export polish open)
- [x] **5c.1** Quaternion plant kinematics + renorm; Euler gentle open-loop parity  
- [x] **5c.2** Error-state / geodesic attitude error in control + metrics  
- [x] **5c.3a** LQR + PID SO(3) error; optional `sim.attitude: quat` plant  
- [x] **5c.3b** Aggressive elevated figure-eight demo (`figure_eight_aggressive`, soft goldens)  
- [x] **5c.4** `DynamicsModel` protocol + plant injection  
- [ ] Export / timeseries schema for native 13-state logging (optional; not required for 5c exit)

### M5d — Observer-in-the-loop (**done** for stretch goals)
- [x] Measurement noise model (`MeasurementModel`) on Euler state channels  
- [x] `StateObserver` protocol wired in closed-loop (plant → measure → observer → controller)  
- [x] `linear_kf` (hover A/B) + study config `sim.observer` (default `none`)  
- [x] Soft regression: full-state figure-eight unchanged; observer study tracks with soft RMSE band  
- [x] Partial-state channels + H matrix (`channels: [pos, omega, …]`)  
- [x] Error-state MEKF (`type: mekf`) + demo study  
- [x] `x_hat` logged in `nominal/timeseries.npz`

### M6 — Nav beyond waypoints
- [ ] First non-waypoint guidance backend + example study  

### M7 — HIL path (software; rig is parallel Track B)
- [ ] Fixed-step plant + I/O schemas  
- [ ] Transport adapter + timeout policy  
- [ ] SIL vs HIL compare on gentle mission  
- [ ] Rig companion: sensors + bus (when hardware exists)  

---

## 7. Dependencies and risks

| Risk / dependency | Mitigation |
|-------------------|------------|
| Min-snap solver complexity | Start with interp + simple missions; swap solver behind interface |
| Premature HIL | Complete M5 (export/compare) first; HIL is M7 |
| Framework theater | Earn registries with 2nd controller / 2nd guidance family only |
| MC flaky numerics | Soft tolerances; seed discipline; small CI N |
| Scope creep (sensors, multi-vehicle) | Stay in SPEC deferred list until epic prioritized |
| MATLAB heritage pull | Domain reference only; no runtime / no layout copy |
| HIL rig long lead | Advance Phase 5c SIL (quats/plant) while hardware is ordered/built |
| Quaternion breaks 12-state export/MC | Schema version + soft rebaseline; keep Euler path until parity tests green |

---

## 8. Effort sketch (relative)

Rough relative effort for planning only (not estimates to calendar):

| Phase | Relative effort | Notes |
|-------|-----------------|-------|
| 0 | S | Days |
| 1 | M | First real GNC value |
| 2 | M–L | Min-snap is the swing factor |
| 3 | M | Parallelism + schemas |
| 4 | M | Ops/Docker learning curve |
| 5 | S–M | High leverage for workflow story |
| 5c | M–L | State layout + control/metrics; unlocks mission envelope |
| 6 | M | Depends on chosen nav mode |
| 7 | L | Hardware + timing + comparison honesty (rig lead time dominates) |

---

## 9. Explicit non-goals (near term)

- Line-for-line MATLAB port or bit-parity  
- Paper figure pipeline recreation  
- Flight certification or “ready to fly” claims  
- Full web product / multi-vehicle formation  
- Supporting every autopilot vendor  

---

## 10. How to update this roadmap

1. Change **sequencing or priority** here.  
2. Change **requirements / acceptance** in `SPEC.md`.  
3. Change **structure / interfaces** in `docs/ARCHITECTURE.md`.  
4. Note material shifts in SPEC/ARCH changelogs when behavior intent moves.  

Per `GROK.md` GSD: non-trivial work gets a SPEC note before a large implementation pass.

---

## 11. Changelog

| Date | Notes |
|------|--------|
| 2026-07-18 | Initial roadmap from SPEC v0.2 / ARCH v0.4; M0–M7 checklist |
| 2026-07-18 | Phase 0 / M0 complete; next is Phase 1 SIL |
| 2026-07-18 | Phase 1 / M1 complete: hover SIL, LQR, run artifacts, `uavsim simulate` |
| 2026-07-18 | Phase 2 / M2 complete: waypoints, Akima interp, min-snap, auto, feasibility, registries |
| 2026-07-18 | Phase 3 / M3 complete: local MC, `uavsim study`/`report`, trial table + summary |
| 2026-07-18 | Phase 4 / M4 complete: Docker image, sharded MC + merge, compose demo |
| 2026-07-18 | Phase 5 / M5 complete: controller export, compare, PID cascade second law |
| 2026-07-19 | Phase 5b / M5b: viz pack V1–V8 (interactive 3D, MC plots, feasibility, stills) |
| 2026-07-20 | Document multi-airframe / HIL-rig research track (§5.1); developer airframes guide |
| 2026-07-20 | Promote Phase **5c** (quaternions + plant fidelity) to **Now**; HIL rig parallel Track B; flex/motors after 5c |
| 2026-07-21 | Promote **observer-in-the-loop (5d)** from deferred to scoped SIL (KF/EKF); order after 5c plant seams |
| 2026-07-21 | 5c/5d marked done in status; README + estimation.md updated for observers/quat |
| 2026-07-20 | Docs audit: phase table + Now track → motors/mixer; M5c title Done; cross-link developer hub |
