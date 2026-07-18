# ROADMAP — `uavsim` / quadrotor-sim

**Status:** Active  
**Last updated:** 2026-07-18  
**Normative detail:** [`SPEC.md`](SPEC.md) (requirements, stories, acceptance) · [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) (how) · [`GROK.md`](GROK.md) (process)

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
| HIL / post-core nav | **Not started** ← **now Phase 6+** |

---

## 4. Delivery phases

Phases are **capability gates**, not calendar dates. Prefer finishing a gate’s exit signals before starting the next large chunk (small spikes OK).

| Phase | Name | Epics | Exit signals (short) | Priority |
|-------|------|-------|----------------------|----------|
| **0** | Stand-up | — | `uv` package `uavsim`, pytest, ruff, CI stub, thin CLI | **Now** |
| **1** | SIL physics loop | A, C | Vehicle + dynamics + LQR + trivial reference + run dir + `simulate`; SIL adapter seam | **Next** |
| **2** | Guidance + control interface | B, C | Waypoints, interp/min-snap, feasibility, registries, ≥3 missions | Core |
| **3** | Robustness | C, F | Local MC, `study`, seed-stable smoke, plots-as-consumer | Core |
| **4** | Systems | F | Docker study + sharded MC assemble | Core (systems-heavy) |
| **5** | Workflow polish | D, E-SIL | **Export** + **`compare`** two SIL runs; second controller if not done | Core Should |
| **6** | Nav expansion | B+ | First non-waypoint guidance | Post-core |
| **7** | HIL / PIL | E | Fixed-step + transport + SIL↔HIL via export/compare | Post-core |

Detail and MoSCoW: SPEC §6, §19. Module map: ARCH §3, §16.

---

## 5. Now / next / later

### Now
1. **Phase 6** — first non-waypoint guidance backend (optional portfolio extender).  
2. Keep SPEC/ARCH/ROADMAP in sync when decisions change.

### Next
1. Phase 7 HIL path (fixed-step + transport + SIL↔HIL compare).  
2. Freeze timeseries format lean (Parquet) when needed (NPZ today).

### Later (post-core, prioritize by portfolio need)
1. Phase 6 non-waypoint guidance (geometric is a likely first step).  
2. Phase 7 HIL transport (UDP loopback fixture before real FC).  
3. Optional polyglot hotspot (min-snap / dynamics).  
4. Queue backends, richer gallery UI.

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

### M6 — Nav beyond waypoints
- [ ] First non-waypoint guidance backend + example study  

### M7 — HIL path
- [ ] Fixed-step plant + I/O schemas  
- [ ] Transport adapter + timeout policy  
- [ ] SIL vs HIL compare on gentle mission  

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
| 6 | M | Depends on chosen nav mode |
| 7 | L | Hardware + timing + comparison honesty |

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
